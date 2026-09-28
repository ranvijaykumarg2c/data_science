import json
from pathlib import Path
from collections import Counter

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================


# Base Directory
DATA_DIR = Path("Data/Output")


FILES = {
    "Artwork": DATA_DIR / "artwork_daily_sale.json",
    "Cars": DATA_DIR / "cars_daily_sale.json",
    "Memorabilia": DATA_DIR / "memorabilia_daily_sale.json",
}

REPORT_DIR = DATA_DIR / "Inspection"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_json(file_path):
    """Load a JSON file and return it as a list of records."""

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Handle common cases where records are nested in a dictionary
        for key in ["data", "records", "results", "items"]:
            if key in data and isinstance(data[key], list):
                return data[key]

        return [data]

    raise ValueError(f"Unexpected JSON structure in {file_path}")


def is_missing(value):
    """Identify common missing-value representations."""

    if value is None:
        return True

    if isinstance(value, str):
        cleaned = value.strip().lower()

        return cleaned in {
            "",
            "n/a",
            "na",
            "none",
            "null",
            "nan",
            "nll",
        }

    return False


def percentage(part, total):
    if total == 0:
        return 0

    return round((part / total) * 100, 2)


# ============================================================
# BASIC INSPECTION
# ============================================================

def inspect_basic(asset_name, records):
    print("\n" + "=" * 80)
    print(f"{asset_name.upper()} - BASIC INFORMATION")
    print("=" * 80)

    df = pd.DataFrame(records)

    print(f"Rows:    {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    print("\nColumns:")
    for i, column in enumerate(df.columns, start=1):
        print(f"  {i:3}. {column}")

    return df


# ============================================================
# DATA TYPES
# ============================================================

def inspect_data_types(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - DATA TYPES")
    print("-" * 80)

    for column in df.columns:
        print(f"{column:35} {str(df[column].dtype)}")


# ============================================================
# MISSING VALUES
# ============================================================

def inspect_missing_values(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - MISSING VALUES")
    print("-" * 80)

    total_rows = len(df)

    results = []

    for column in df.columns:
        missing_count = sum(
            is_missing(value)
            for value in df[column]
        )

        results.append({
            "field": column,
            "missing_count": missing_count,
            "missing_percent": percentage(
                missing_count,
                total_rows
            ),
        })

    missing_df = pd.DataFrame(results)

    missing_df = missing_df.sort_values(
        "missing_percent",
        ascending=False
    )

    print(
        missing_df.to_string(index=False)
    )

    return missing_df


# ============================================================
# ASSET TYPE
# ============================================================

def inspect_asset_type(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - ASSET TYPE")
    print("-" * 80)

    if "asset_type" not in df.columns:
        print("asset_type field not found.")
        return

    counts = df["asset_type"].value_counts(dropna=False)

    print(counts.to_string())


# ============================================================
# CURRENCIES
# ============================================================

def inspect_currency(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - CURRENCIES")
    print("-" * 80)

    if "currency" not in df.columns:
        print("currency field not found.")
        return

    values = []

    for value in df["currency"]:
        if is_missing(value):
            values.append("<MISSING>")
        else:
            values.append(str(value).strip().upper())

    counts = Counter(values)

    for currency, count in counts.most_common():
        print(
            f"{currency:20} {count:>10,} "
            f"({percentage(count, len(df))}%)"
        )


# ============================================================
# DATE INSPECTION
# ============================================================

def inspect_dates(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - SALE DATE")
    print("-" * 80)

    if "sale_date" not in df.columns:
        print("sale_date field not found.")
        return

    dates = pd.to_datetime(
        df["sale_date"],
        errors="coerce"
    )

    valid_dates = dates.dropna()

    print(
        f"Valid dates:   {len(valid_dates):,} "
        f"({percentage(len(valid_dates), len(df))}%)"
    )

    print(
        f"Missing/invalid: {len(df) - len(valid_dates):,} "
        f"({percentage(len(df) - len(valid_dates), len(df))}%)"
    )

    if len(valid_dates) > 0:
        print(f"Earliest date: {valid_dates.min()}")
        print(f"Latest date:   {valid_dates.max()}")

        print("\nRecords by year:")
        print(
            valid_dates.dt.year
            .value_counts()
            .sort_index()
            .to_string()
        )


# ============================================================
# PRICE FIELD INSPECTION
# ============================================================

def inspect_price_fields(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - PRICE / ESTIMATE FIELDS")
    print("-" * 80)

    price_fields = [
        "ah_low_estimate",
        "ah_high_estimate",
        "ah_bp_price",
        "ah_price",
        "ah_low_estimate_usd",
        "ah_high_estimate_usd",
        "ah_bp_price_usd",
        "ah_price_usd",
    ]

    for field in price_fields:

        if field not in df.columns:
            print(f"\n{field}: NOT FOUND")
            continue

        missing_count = sum(
            is_missing(value)
            for value in df[field]
        )

        numeric_values = pd.to_numeric(
            df[field],
            errors="coerce"
        )

        valid_numeric = numeric_values.notna().sum()
        zero_count = (numeric_values == 0).sum()
        negative_count = (numeric_values < 0).sum()

        print(f"\n{field}")
        print(f"  Valid numeric: {valid_numeric:,} "
              f"({percentage(valid_numeric, len(df))}%)")
        print(f"  Missing/non-numeric: {len(df) - valid_numeric:,} "
              f"({percentage(len(df) - valid_numeric, len(df))}%)")
        print(f"  Zero values: {zero_count:,}")
        print(f"  Negative values: {negative_count:,}")

        if valid_numeric > 0:
            print(f"  Minimum: {numeric_values.min()}")
            print(f"  Maximum: {numeric_values.max()}")


# ============================================================
# DUPLICATE INSPECTION
# ============================================================

def inspect_duplicates(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - DUPLICATES")
    print("-" * 80)

    duplicate_fields = [
        "ID",
        "lot_url",
        "auction_url",
    ]

    for field in duplicate_fields:

        if field not in df.columns:
            continue

        valid_values = df[field].apply(
            lambda x: not is_missing(x)
        )

        series = df.loc[valid_values, field]

        duplicate_count = series.duplicated(keep=False).sum()

        unique_count = series.nunique()

        print(f"\n{field}")
        print(f"  Non-missing values: {len(series):,}")
        print(f"  Unique values:      {unique_count:,}")
        print(f"  Duplicate rows:     {duplicate_count:,}")


# ============================================================
# AUCTION HOUSE INSPECTION
# ============================================================

def inspect_auction_houses(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - AUCTION HOUSES")
    print("-" * 80)

    if "auction_house" not in df.columns:
        print("auction_house field not found.")
        return

    values = []

    for value in df["auction_house"]:
        if is_missing(value):
            values.append("<MISSING>")
        else:
            values.append(str(value).strip())

    counts = Counter(values)

    print(f"Unique values: {len(counts):,}\n")

    for house, count in counts.most_common(30):
        print(
            f"{house[:60]:60} "
            f"{count:>10,}"
        )


# ============================================================
# SUSPICIOUS RECORD CHECKS
# ============================================================

def inspect_suspicious_records(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - BASIC DATA QUALITY FLAGS")
    print("-" * 80)

    # Low estimate > high estimate
    if (
        "ah_low_estimate" in df.columns
        and "ah_high_estimate" in df.columns
    ):
        low = pd.to_numeric(
            df["ah_low_estimate"],
            errors="coerce"
        )

        high = pd.to_numeric(
            df["ah_high_estimate"],
            errors="coerce"
        )

        invalid_estimates = (
            low.notna()
            & high.notna()
            & (low > high)
        )

        print(
            f"Low estimate > high estimate: "
            f"{invalid_estimates.sum():,}"
        )

    # Negative prices
    price_fields = [
        "ah_low_estimate",
        "ah_high_estimate",
        "ah_bp_price",
        "ah_price",
    ]

    for field in price_fields:

        if field not in df.columns:
            continue

        values = pd.to_numeric(
            df[field],
            errors="coerce"
        )

        negative = (values < 0).sum()

        if negative:
            print(
                f"Negative values in {field}: "
                f"{negative:,}"
            )

    # Asset type mismatch inside file
    if "asset_type" in df.columns:

        expected = asset_name

        mismatch = (
            df["asset_type"].astype(str).str.lower()
            != expected.lower()
        )

        print(
            f"Asset-type mismatches: "
            f"{mismatch.sum():,}"
        )


# ============================================================
# SAMPLE RECORDS
# ============================================================

def show_samples(asset_name, df):
    print("\n" + "-" * 80)
    print(f"{asset_name.upper()} - SAMPLE RECORDS")
    print("-" * 80)

    if len(df) == 0:
        return

    sample = df.head(3)

    for index, row in sample.iterrows():
        print(f"\nRecord {index + 1}:")

        for column, value in row.items():
            print(f"  {column}: {value}")


# ============================================================
# SAVE CSV REPORTS
# ============================================================

def save_reports(asset_name, df, missing_df):
    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_name = asset_name.lower()

    # Missing-value report
    missing_path = (
        REPORT_DIR /
        f"{safe_name}_missing_values.csv"
    )

    missing_df.to_csv(
        missing_path,
        index=False
    )

    # Column list
    columns_path = (
        REPORT_DIR /
        f"{safe_name}_columns.csv"
    )

    columns_df = pd.DataFrame({
        "column": df.columns,
        "data_type": [
            str(df[column].dtype)
            for column in df.columns
        ],
    })

    columns_df.to_csv(
        columns_path,
        index=False
    )

    print(
        f"\nReports saved:"
        f"\n  {missing_path}"
        f"\n  {columns_path}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 80)
    print("GCS EXTRACTED DATA - INSPECTION REPORT")
    print("=" * 80)

    print("\nRaw files will NOT be modified.")

    all_data = {}

    for asset_name, file_path in FILES.items():

        print("\n\n")
        print("#" * 80)
        print(f"# {asset_name.upper()}")
        print(f"# File: {file_path}")
        print("#" * 80)

        if not file_path.exists():
            print(
                f"\nERROR: File not found:\n"
                f"{file_path}"
            )
            continue

        try:
            records = load_json(file_path)

            all_data[asset_name] = records

            df = inspect_basic(
                asset_name,
                records
            )

            inspect_data_types(
                asset_name,
                df
            )

            missing_df = inspect_missing_values(
                asset_name,
                df
            )

            inspect_asset_type(
                asset_name,
                df
            )

            inspect_currency(
                asset_name,
                df
            )

            inspect_dates(
                asset_name,
                df
            )

            inspect_price_fields(
                asset_name,
                df
            )

            inspect_duplicates(
                asset_name,
                df
            )

            inspect_auction_houses(
                asset_name,
                df
            )

            inspect_suspicious_records(
                asset_name,
                df
            )

            show_samples(
                asset_name,
                df
            )

            save_reports(
                asset_name,
                df,
                missing_df
            )

        except Exception as e:
            print(
                f"\nERROR while inspecting "
                f"{asset_name}: {e}"
            )

    # ========================================================
    # CROSS-ASSET SCHEMA COMPARISON
    # ========================================================

    print("\n\n")
    print("#" * 80)
    print("# CROSS-ASSET SCHEMA COMPARISON")
    print("#" * 80)

    schema = {}

    for asset_name, records in all_data.items():
        df = pd.DataFrame(records)
        schema[asset_name] = set(df.columns)

    all_columns = sorted(
        set().union(*schema.values())
    )

    schema_rows = []

    for column in all_columns:

        row = {
            "field": column
        }

        for asset_name in FILES.keys():
            row[asset_name] = (
                "YES"
                if column in schema.get(
                    asset_name,
                    set()
                )
                else "NO"
            )

        schema_rows.append(row)

    schema_df = pd.DataFrame(schema_rows)

    print(
        "\n"
        + schema_df.to_string(index=False)
    )

    schema_path = (
        REPORT_DIR /
        "cross_asset_schema_comparison.csv"
    )

    schema_df.to_csv(
        schema_path,
        index=False
    )

    print(
        f"\nSchema comparison saved to:\n"
        f"{schema_path}"
    )

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)

    print(
        "\nNo raw JSON files were modified."
    )


if __name__ == "__main__":
    main()