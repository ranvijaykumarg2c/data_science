"""Download v2 daily-sale JSON files for one asset type.

Expects GCS object paths like <auction house>/<asset type>/<filename>.
Discovers matching houses, selects JSON filenames containing v2, and exports
new-schema files by default. No sale-date filter or deduplication is applied.

This script is self-contained. Install pandas and google-cloud-storage.

Example:
    python daily_sale_retriever.py --asset-type Watch --output exports/watch.json

See README-retrievers.md for local setup and authentication. Asset names must
match bucket folder capitalization. Outputs are local files, not GCS uploads.
"""

import argparse

from io import BytesIO
from pathlib import Path
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


def main():
    """Retrieve one asset across auction houses and export its selected schema."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--bucket", default="daily_auction_sales", help="GCS bucket name, without gs://")
    parser.add_argument("--asset-type", default="Memorabilia", help="Case-sensitive bucket folder name")
    parser.add_argument("--schema", choices=["old", "new", "all"], default="new", help="File schema: old lacks auction_url; new contains it; all keeps both")
    parser.add_argument("--output", help="Default: Data/Output/<asset>_daily_sale.json")
    add_connection_arguments(parser)
    args = parser.parse_args()
    # Derive the filename from the asset unless the caller supplies --output.
    # Paths are relative to the working directory; an existing file is replaced.
    output = args.output or f"Data/Output/{asset_slug(args.asset_type)}_daily_sale.json"
    bucket = client_for(args).bucket(args.bucket)
    frame = collect(daily_blobs(bucket, args.asset_type), schema=args.schema, v2_only=True, fail_fast=args.fail_fast)
    export_json(frame, output)


if __name__ == "__main__":
    run(main)
