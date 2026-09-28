"""Download JSON records from a GCP bucket; defaults to daily_auction_sales.

Use this runner for a whole bucket or a known object prefix. It does not
filter by asset type, year, or a v2 filename. The default selects old-schema
files (those without an auction_url column); --schema all includes both schemas.

Example:
    python bucket_retriever.py --schema all --output exports/daily_sales.json

This script is self-contained. Install pandas and google-cloud-storage.
Setup and authentication: see README-retrievers.md. Output paths are local,
relative to the directory you run from; existing output files are overwritten.
"""

import argparse

from io import BytesIO
from pathlib import Path
import sys

import pandas as pd
from google.cloud import storage


# Local helpers: this script can be copied and run on its own.
def add_connection_arguments(parser):
    """Add project and per-file failure options to an ArgumentParser."""
    parser.add_argument("--project", help="Optional Google Cloud project ID")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first file error")


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
    """Parse options, download the selected JSON files, and save one dataset."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # Defaults can be overridden on the command line without editing this file.
    parser.add_argument("--bucket", default="daily_auction_sales", help="GCS bucket name, without gs://")
    parser.add_argument("--prefix", default="", help="Optional object prefix")
    parser.add_argument("--schema", choices=["old", "new", "all"], default="old", help="File schema: old lacks auction_url; new contains it; all keeps both")
    parser.add_argument("--output", default="Data/Output/daily_auction_sales_bucket.json", help="Local JSON destination; existing file is overwritten")
    add_connection_arguments(parser)
    args = parser.parse_args()
    # An empty prefix scans the entire bucket, including nested object paths.
    bucket = client_for(args).bucket(args.bucket)
    frame = collect(bucket.list_blobs(prefix=args.prefix or None), schema=args.schema, fail_fast=args.fail_fast)
    export_json(frame, args.output)


if __name__ == "__main__":
    run(main)
