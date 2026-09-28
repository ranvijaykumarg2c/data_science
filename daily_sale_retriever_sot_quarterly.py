"""Export one year of new-schema daily sales and quarterly row counts.

Reads <auction house>/<asset type>/ object paths, selecting JSON filenames
containing v2 and files with an auction_url column. Here 'SoT' describes that
schema convention; it does not guarantee validated records or complete URLs.

This script is self-contained. Install pandas and google-cloud-storage.

Example:
    python daily_sale_retriever_sot_quarterly.py --asset-type Watch --year 2025

Writes <asset>_daily_sale_sot_<year>.json and
<asset>_daily_sale_sot_quarter_counts_<year>.csv to --output-dir.
See README-retrievers.md for setup. Existing output files are overwritten.
"""

import argparse
from pathlib import Path

from io import BytesIO
import re
import sys

import pandas as pd
from google.cloud import storage


# Local helpers: this script can be copied and run on its own.
def add_connection_arguments(parser):
    """Add project and per-file failure options to an ArgumentParser."""
    parser.add_argument("--project", help="Optional Google Cloud project ID")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first file error")


def asset_slug(asset_type):
    """Return a filename component, e.g. 'Memorabilia' becomes 'memorabilia'.

    This only changes output names; GCS asset folder matching uses the original
    string. Raise ValueError if no ASCII letters or digits remain.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", asset_type.lower()).strip("_")
    if not slug:
        raise ValueError("Asset type must contain letters or numbers")
    return slug


def client_for(args):
    """Create a Storage client using args.project and ambient credentials.

    With project=None, the SDK infers the project from the local environment.
    The caller needs permissions to list and read the chosen bucket's objects.
    """
    # Uses Application Default Credentials; no credentials are embedded here.
    return storage.Client(project=args.project)


def collect(blobs, schema="new", v2_only=False, fail_fast=False):
    """Download selected files and return one concatenated pandas DataFrame.

    Args:
        blobs: Iterable of GCS Blob objects (such as bucket.list_blobs()).
        schema: 'old' excludes files with an auction_url column; 'new' requires
            that column; 'all' includes both. Individual URL values aren't checked.
        v2_only: Require the case-sensitive substring 'v2' in the object name.
        fail_fast: Re-raise the first download/parse error instead of skipping it.

    Only .json objects are parsed; JSON Lines is not enabled. Different columns
    are combined by name, leaving missing values where schemas differ. Duplicate
    rows/IDs are retained. All selected frames are held in memory.

    Raises ValueError if no files match. Listing failures propagate; per-file
    failures otherwise print to stderr and allow a partial export. Printed counts
    distinguish listed objects, parsed JSON files, selected files, and failures.
    """
    frames = []
    scanned = parsed = selected = errors = 0
    for blob in blobs:
        scanned += 1
        if not blob.name.lower().endswith(".json"):
            continue
        if v2_only and "v2" not in blob.name:
            continue
        try:
            raw = blob.download_as_bytes()
            if not raw.strip():
                raise ValueError("Empty file")
            frame = pd.read_json(BytesIO(raw))
        except Exception as exc:
            errors += 1
            print(f"Failed: {blob.name}: {exc}", file=sys.stderr)
            if fail_fast:
                raise
            continue
        parsed += 1
        # This is a file-level schema heuristic, not a data-quality check.
        is_new = "auction_url" in frame.columns
        if schema == "all" or (schema == "new" and is_new) or (schema == "old" and not is_new):
            frames.append(frame)
            selected += 1
    print(f"Scanned: {scanned}; parsed: {parsed}; selected: {selected}; failed: {errors}")
    if not frames:
        raise ValueError("No files matched the selected schema and filters; no export written.")
    result = pd.concat(frames, ignore_index=True, sort=False)
    print(f"Selected rows: {len(result):,}")
    if errors:
        print("WARNING: Export is partial because some files failed.", file=sys.stderr)
    return result


def daily_blobs(bucket, asset_type):
    """Yield blobs under each discovered house's case-sensitive asset folder.

    This first lists the entire bucket to discover houses, then lists each
    matching prefix. It expects house/asset/file paths and does not download
    object contents; collect() handles downloading and filename selection.
    """
    houses = set()
    for blob in bucket.list_blobs():
        parts = blob.name.split("/")
        if len(parts) >= 2 and parts[1] == asset_type:
            houses.add(parts[0])
    print(f"Auction houses found for {asset_type}: {sorted(houses)}")
    for house in sorted(houses):
        print(f"Scanning: {house}")
        yield from bucket.list_blobs(prefix=f"{house}/{asset_type}/")


def export_json(frame, path):
    """Write a DataFrame as a local JSON array of records, replacing the file.

    Create missing parent folders. Datetime columns use ISO strings; other
    values retain pandas' JSON serialization behavior. Writes are not atomic.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_json(path, orient="records", indent=4, date_format="iso")
    print(f"Saved {len(frame):,} rows to {path}")


def run(main):
    """Invoke a runner and turn uncaught errors/interruptions into exit code 1.

    argparse handles --help and argument errors itself. Skipped file failures
    do not cause a nonzero exit unless --fail-fast is used; inspect warnings
    when accepting a partial export. Tracebacks are suppressed for CLI clarity.
    """
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)


def year_and_quarters(frame, year):
    """Return (year_rows, quarter_counts) without modifying the input frame.

    Require sale_date, parse mixed date strings in UTC, and coerce invalid
    dates to NaT. Missing/invalid dates and dates outside year are excluded.
    year_rows gains a quarter column; quarter_counts always includes Q1-Q4,
    including zero-count quarters. An unmatched year returns an empty dataset.
    Counts are row counts, with no deduplication or sold-lot filtering.
    """
    if "sale_date" not in frame.columns:
        raise ValueError("Expected a sale_date column")
    frame = frame.copy()
    frame["sale_date"] = pd.to_datetime(frame["sale_date"], errors="coerce", format="mixed", utc=True)
    print(f"Missing or invalid sale dates excluded: {frame['sale_date'].isna().sum():,}")
    result = frame.loc[frame["sale_date"].dt.year == year].copy()
    result["quarter"] = "Q" + result["sale_date"].dt.quarter.astype(str)
    # Reindex so the CSV has a stable order and includes quarters with no rows.
    counts = (result["quarter"].value_counts().reindex(["Q1", "Q2", "Q3", "Q4"], fill_value=0)
              .rename_axis("quarter").reset_index(name="count"))
    return result, counts


def main():
    """Download SoT files, filter by UTC sale year, and write JSON plus CSV."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--bucket", default="daily_auction_sales", help="GCS bucket name, without gs://")
    parser.add_argument("--asset-type", default="Watch", help="Case-sensitive bucket folder name")
    parser.add_argument("--year", type=int, default=2025, help="Sale year to retain after parsing dates in UTC")
    parser.add_argument("--output-dir", type=Path, default=Path("Data/Output"), help="Local directory for JSON and quarter-count CSV")
    add_connection_arguments(parser)
    args = parser.parse_args()
    if not 1 <= args.year <= 9999:
        parser.error("--year must be between 1 and 9999")
    slug = asset_slug(args.asset_type)
    bucket = client_for(args).bucket(args.bucket)
    frame = collect(daily_blobs(bucket, args.asset_type), schema="new", v2_only=True, fail_fast=args.fail_fast)
    # Invalid/missing dates are reported and excluded. Counts include duplicate
    # records and represent this retrieval's rows, not total market sales.
    selected, counts = year_and_quarters(frame, args.year)
    print(counts.to_string(index=False))
    # export_json creates the directory before the CSV is written beside it.
    export_json(selected, args.output_dir / f"{slug}_daily_sale_sot_{args.year}.json")
    path = args.output_dir / f"{slug}_daily_sale_sot_quarter_counts_{args.year}.csv"
    counts.to_csv(path, index=False)
    print(f"Saved quarter counts to {path}")


if __name__ == "__main__":
    run(main)
