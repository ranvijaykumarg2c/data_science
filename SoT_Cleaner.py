from google.cloud import storage
from io import BytesIO
import pandas as pd
from typing import Iterable


def load_auction_sales_by_asset(
    bucket_name: str,
    asset_type: str,
    storage_client: storage.Client | None = None,
    new_key_col: str = "auction_url",
):
    """
    Scan a GCS bucket for auction sales JSONs by asset type,
    split into old-key and new-key dataframes.

    Returns
    -------
    non_sot_df : pd.DataFrame
        Data using old keys (no `new_key_col`)
    sot_df : pd.DataFrame
        Data using new keys (contains `new_key_col`)
    auction_houses : list[str]
        Auction houses found for the asset type
    """

    if storage_client is None:
        storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    old_data = []
    new_data = []

    # Step 1: discover auction houses dynamically
    prefix_set = set()
    for blob in bucket.list_blobs():
        parts = blob.name.split("/")
        if len(parts) >= 2 and parts[1] == asset_type:
            prefix_set.add(parts[0])

    auction_houses = sorted(prefix_set)
    print(f"Auction houses found for {asset_type}: {auction_houses}")

    # Step 2: scan each auction house
    for house in auction_houses:
        prefix = f"{house}/{asset_type}/"
        print("-" * 20)
        print("Scanning:", house)

        file_count = 0
        final_sale_count = 0

        for blob in bucket.list_blobs(prefix=prefix):
            file_count += 1

            if "v2" in blob.name:
                final_sale_count += 1
                data = blob.download_as_bytes()
                df = pd.read_json(BytesIO(data))

                if new_key_col not in df.columns:
                    old_data.append(df)
                else:
                    new_data.append(df)

        print(f"Total files found in {house}: {file_count}")
        print(f"Total (v2) files found in {house}: {final_sale_count}")

    print("\nNON-SOT JSON COUNT:", len(old_data))
    print("SOT JSON COUNT:", len(new_data))

    non_sot_df = (
        pd.concat(old_data, ignore_index=True, sort=False)
        if old_data else pd.DataFrame()
    )
    sot_df = (
        pd.concat(new_data, ignore_index=True, sort=False)
        if new_data else pd.DataFrame()
    )

    return non_sot_df, sot_df


def load_historical_training_data(bucket_name: str, identifier: str) -> pd.DataFrame:
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    dfs = []

    for blob in bucket.list_blobs():
        if identifier in blob.name and blob.name.endswith(".json"):
            data = blob.download_as_bytes()
            dfs.append(pd.read_json(BytesIO(data)))

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


class BaseAssetPreprocessor:
    """
    Base class for asset-specific preprocessors
    with step-level logging.
    """

    REQUIRED_COLUMNS: set[str] = set()

    def __init__(self, df: pd.DataFrame, verbose: bool = True):
        self.df = df.copy()
        self.verbose = verbose
        self._step = 0

    # ---------- internal helpers ----------

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _next_step(self, title: str):
        self._step += 1
        self._log(f"\n[{self._step}] {title}")

    def _snapshot(self):
        return set(self.df.columns), len(self.df)

    # ---------- chainable operations ----------

    def drop_columns(self, cols: Iterable[str]):
        self._next_step("Drop columns")

        before_cols, before_rows = self._snapshot()

        self.df.drop(list(cols), axis=1, inplace=True, errors="ignore")

        after_cols, after_rows = self._snapshot()
        dropped = sorted(before_cols - after_cols)

        self._log(f"  Columns dropped ({len(dropped)}): {dropped}")
        self._log(f"  Rows affected: {before_rows} → {after_rows}")

        return self

    def rename_columns(self, mapping: dict):
        self._next_step("Rename columns")

        before_cols, before_rows = self._snapshot()

        self.df.rename(columns=mapping, inplace=True)

        after_cols, _ = self._snapshot()

        applied = {k: v for k, v in mapping.items() if k in before_cols}

        self._log(f"  Columns renamed ({len(applied)}): {applied}")
        self._log(f"  Rows affected: {before_rows}")

        return self


    def add_missing_columns(self, cols: dict):
        """
        Add missing columns with per-column default values.
    
        Example:
            add_missing_columns({
                "auction_url": None,
                "data_source": "historical",
            })
        """
    
        self._next_step("Add missing columns")
    
        before_cols, before_rows = self._snapshot()
    
        added = []
        for col, value in cols.items():
            if col not in self.df.columns:
                self.df[col] = value
                added.append(col)
    
        after_cols, after_rows = self._snapshot()
    
        self._log(f"  Columns added ({len(added)}): {added}")
        self._log(f"  Rows affected: {before_rows} → {after_rows}")
    
        return self


    def drop_na_required(self):
        if not self.REQUIRED_COLUMNS:
            return self

        self._next_step("Drop rows with missing REQUIRED_COLUMNS")

        before_cols, before_rows = self._snapshot()

        self.df = self.df.dropna(subset=self.REQUIRED_COLUMNS)

        after_cols, after_rows = self._snapshot()

        removed = before_rows - after_rows

        self._log(f"  Required columns: {sorted(self.REQUIRED_COLUMNS)}")
        self._log(f"  Rows removed: {removed}")
        self._log(f"  Rows remaining: {after_rows}")

        return self

    def normalize_na_values(self, na_values: set[str] | None = None):
        """
        Normalize common null-like values across all columns.
        """
        self._next_step("Normalize null-like values")

        before_cols, before_rows = self._snapshot()
        before_nulls = int(self.df.isna().sum().sum())

        na_tokens = na_values or {
            "n/a",
            "na",
            "none",
            "<n/a>",
            "<na>",
            "nan",
            "null",
            "<null>",
            "missing",
            "undef",
            "undefined",
            "not available",
            "",
        }

        def _normalize(val):
            if isinstance(val, str):
                return None if val.strip().lower() in na_tokens else val
            return None if pd.isna(val) else val

        if hasattr(self.df, "map"):
            # pandas >= 2.1
            self.df = self.df.map(_normalize)
        else:
            # older pandas
            self.df = self.df.applymap(_normalize)

        after_cols, after_rows = self._snapshot()
        after_nulls = int(self.df.isna().sum().sum())

        self._log(f"  Rows affected: {before_rows} → {after_rows}")
        self._log(f"  New nulls added: {after_nulls - before_nulls}")
        return self

    def to_datetime(self, cols: Iterable[str], errors: str = "coerce"):
        self._next_step("Convert columns to datetime")

        before_cols, before_rows = self._snapshot()

        converted = []
        for col in cols:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors=errors)
                converted.append(col)

        self._log(f"  Columns converted ({len(converted)}): {converted}")
        self._log(f"  Rows affected: {before_rows}")
        return self

    def filter_year_gte(self, date_col: str, min_year: int):
        self._next_step(f"Filter rows where {date_col}.year >= {min_year}")

        before_cols, before_rows = self._snapshot()

        if date_col not in self.df.columns:
            self._log(f"  Skipped: missing column `{date_col}`")
            self._log(f"  Rows affected: {before_rows} → {before_rows}")
            return self

        dates = pd.to_datetime(self.df[date_col], errors="coerce")
        self.df = self.df[dates.dt.year >= min_year].copy()

        after_cols, after_rows = self._snapshot()
        self._log(f"  Rows affected: {before_rows} → {after_rows}")
        return self

    def combine_name_columns(self, first_col: str, last_col: str, out_col: str = "artist_name"):
        self._next_step(f"Build `{out_col}` from `{first_col}` + `{last_col}`")

        before_cols, before_rows = self._snapshot()

        if first_col not in self.df.columns or last_col not in self.df.columns:
            self._log("  Skipped: missing one or both source columns")
            self._log(f"  Rows affected: {before_rows}")
            return self

        self.df[out_col] = (
            self.df[first_col].fillna("").astype(str)
            + " "
            + self.df[last_col].fillna("").astype(str)
        ).str.strip()
        self.df[out_col] = self.df[out_col].replace("", pd.NA)

        self._log(f"  Column created/updated: {out_col}")
        self._log(f"  Rows affected: {before_rows}")
        return self

    def drop_duplicates_rows(self, subset: Iterable[str], keep: str = "first"):
        self._next_step("Drop duplicate rows")

        before_cols, before_rows = self._snapshot()

        subset_list = [col for col in subset if col in self.df.columns]
        if not subset_list:
            self._log("  Skipped: no subset columns found")
            self._log(f"  Rows affected: {before_rows} → {before_rows}")
            return self

        self.df = self.df.drop_duplicates(subset=subset_list, keep=keep).reset_index(drop=True)

        after_cols, after_rows = self._snapshot()
        self._log(f"  Subset used: {subset_list}")
        self._log(f"  Rows affected: {before_rows} → {after_rows}")
        return self

    def filter_notna_and_nonzero(self, col: str):
        self._next_step(f"Filter rows with `{col}` not null and non-zero")

        before_cols, before_rows = self._snapshot()

        if col not in self.df.columns:
            self._log(f"  Skipped: missing column `{col}`")
            self._log(f"  Rows affected: {before_rows} → {before_rows}")
            return self

        self.df = self.df[self.df[col].notna() & (self.df[col] != 0)].copy()

        after_cols, after_rows = self._snapshot()
        self._log(f"  Rows affected: {before_rows} → {after_rows}")
        return self

    # ---------- validation ----------

    def validate_schema(self, other_df: pd.DataFrame) -> bool:
        self._next_step("Validate schema")
        ok = set(self.df.columns) == set(other_df.columns)
        self._log(f"  Schema match: {ok}")
        return ok

    def get_df(self) -> pd.DataFrame:
        self._next_step("Finalize dataframe")
        self._log(f"  Final shape: {self.df.shape}")
        return self.df


class ArtworkPreprocessor(BaseAssetPreprocessor):

    COMPLETE_SOT_COLS = [
        "asset_type",
        "auction_house",
        "sale_id",
        "sale_date",
        "location",
        "auction_title",
        "auction_url",
        "lot_number",
        "currency",
        "ah_low_estimate",
        "ah_high_estimate",
        "ah_bp_price",
        "description_block",
        "image_url",
        "lot_url",
        "ID",
        "ah_low_estimate_usd",
        "ah_high_estimate_usd",
        "ah_bp_price_usd",
        "ah_price",
        "ah_price_usd",
        "artist_name",
        "artist_birth",
        "artist_death",
        "artwork_title",
        "medium",
        "material",
        "length",
        "width",
        "height",
        "unit",
        "signed",
        "dated",
        "titled",
        "year_of_creation",
        "provenance",
        "subject_matter",
        "item_count",
        "edition",
    ]
    
    REQUIRED_COLUMNS = {
        "ah_bp_price_usd",
        "sale_date",
        "artist_name",
        "description_block",
        "year_of_creation",
    }

    RENAME_MAP_NON_SOT = {
        "sale_number": "sale_id",
        "artwork_ah_low_estimate": "ah_low_estimate",
        "artwork_ah_high_estimate": "ah_high_estimate",
        "artwork_ah_bp_price": "ah_bp_price",
        "hammer_price_original": "ah_price",
        "artwork_ah_low_estimate_usd": "ah_low_estimate_usd",
        "artwork_ah_high_estimate_usd": "ah_high_estimate_usd",
        "artwork_ah_price_usd": "ah_bp_price_usd",
        "hammer_price_usd": "ah_price_usd",
        "title": "artwork_title",
        "description": "description_block",
        "date_of_creation": "year_of_creation",
        "link": "lot_url",
    }

    DROP_COLS_NON_SOT = [
        "lot_status",
        "artist_first_name",
        "artist_last_name",
        "including_premium",
        "area",
        "aspect_ratio",
    ]
    
    def enforce_complete_sot_cols(self, fill_value=None):
        """
        Enforce canonical artwork SoT schema:
        - drop columns not in COMPLETE_SOT_COLS
        - add missing columns with `fill_value`
        - reorder columns to COMPLETE_SOT_COLS
        """
        self._next_step("Enforce COMPLETE_SOT_COLS schema")

        before_cols, before_rows = self._snapshot()

        target_cols = list(self.COMPLETE_SOT_COLS)
        target_set = set(target_cols)
        current_set = set(self.df.columns)

        extra_cols = sorted(current_set - target_set)
        missing_cols = [c for c in target_cols if c not in current_set]

        if extra_cols:
            self.df.drop(columns=extra_cols, inplace=True, errors="ignore")

        for col in missing_cols:
            self.df[col] = fill_value

        # Keep canonical output order
        self.df = self.df[target_cols]

        after_cols, after_rows = self._snapshot()
        self._log(f"  Columns dropped ({len(extra_cols)}): {extra_cols}")
        self._log(f"  Columns added ({len(missing_cols)}): {missing_cols}")
        self._log(f"  Rows affected: {before_rows} → {after_rows}")
        return self

    def preprocess_non_sot(
        self,
        add_columns: dict | None = None,
        min_sale_year: int | None = None,
    ):
        required_additions = {"auction_url": None}
        if add_columns:
            required_additions.update(add_columns)

        chain = self.to_datetime(["sale_date"])
        if min_sale_year is not None:
            chain = chain.filter_year_gte("sale_date", min_sale_year)

        return (
            chain.normalize_na_values()
                .combine_name_columns("artist_first_name", "artist_last_name", "artist_name")
                .drop_columns(["medium"])
                .rename_columns({"medium_type": "medium"})
                .rename_columns(self.RENAME_MAP_NON_SOT)
                .add_missing_columns(required_additions)
                .drop_columns(self.DROP_COLS_NON_SOT)
                .drop_na_required()
                .drop_duplicates_rows(["lot_url"])
                .filter_notna_and_nonzero("ah_bp_price_usd")
                .enforce_complete_sot_cols()
        )

    def preprocess_sot(
        self,
        add_columns: dict | None = None,
        min_sale_year: int | None = None,
    ):
        required_additions = {"auction_url": None}
        if add_columns:
            required_additions.update(add_columns)

        chain = self.to_datetime(["sale_date"])
        if min_sale_year is not None:
            chain = chain.filter_year_gte("sale_date", min_sale_year)

        return (
            chain.normalize_na_values()
                .combine_name_columns("artist_first_name", "artist_last_name", "artist_name")
                .drop_columns(["medium"])
                .rename_columns({"medium_type": "medium"})
                .rename_columns({
                    "description": "description_block",
                    "title": "artwork_title",
                    "date_of_creation": "year_of_creation",
                })
                .add_missing_columns(required_additions)
                .drop_columns(self.DROP_COLS_NON_SOT)
                .drop_na_required()
                .drop_duplicates_rows(["lot_url"])
                .filter_notna_and_nonzero("ah_bp_price_usd")
                .enforce_complete_sot_cols()
        )


class WatchPreprocessor(BaseAssetPreprocessor):

    REQUIRED_COLUMNS = {
        "brand",
        "model",
        "description_block",
        "sale_date",
        "ah_bp_price_usd",
    }

    # DROP TARGETS FIRST — they already exist upstream
    DROP_CANONICAL_BEFORE_RENAME = [
        "lot_url",
        "ah_bp_price",
        "ah_price",
        "ah_price_usd",
        "ah_bp_price_usd",
    ]

    RENAME_MAP_NON_SOT = {
        "sale_number": "sale_id",
        "size": "case_size",
        "watch_low_estimate": "ah_low_estimate",
        "watch_high_estimate": "ah_high_estimate",
        "watch_low_estimate_usd": "ah_low_estimate_usd",
        "watch_high_estimate_usd": "ah_high_estimate_usd",
        "hammer_price_bp": "ah_bp_price",
        "hammer_price_original": "ah_price",
        "hammer_price_usd": "ah_price_usd",
        "price_final_usd": "ah_bp_price_usd",
        "link": "lot_url",
    }

    # DROP RAW + NOISE AFTER RENAME
    DROP_COLS_NON_SOT = [
        "hammer_price_bp",
        "hammer_price_original",
        "hammer_price_usd",
        "price_final_usd",

        "watch_ah_low_estimate",
        "watch_ah_high_estimate",
        "watch_ah_low_estimate_usd",
        "watch_ah_high_estimate_usd",

        "bought_in",
        "year",
        "month",
        "Marketplace",
        "country_code",
        "wc_value",
        "auction_date",
    ]

    
    
    DROP_COLS_SOT = [
        "bought_in",
        "hammer_price_bp",
        "hammer_price_original",
    ]

    def preprocess_non_sot(self, add_columns: dict | None = None):
        return (
            self.drop_columns(self.DROP_CANONICAL_BEFORE_RENAME)
                .rename_columns(self.RENAME_MAP_NON_SOT)
                .drop_columns(self.DROP_COLS_NON_SOT)
                .add_missing_columns(add_columns or {})
                .drop_na_required()
        )


    def preprocess_sot(self):
        return (
            self.drop_columns(self.DROP_COLS_SOT)
                .drop_na_required()
        )

class DiamondPreprocessor(BaseAssetPreprocessor):

    REQUIRED_COLUMNS = {
        "description_block",
        "ah_bp_price_usd",
        "sale_date"
    }

    # DROP TARGETS FIRST — they already exist upstream
    DROP_CANONICAL_BEFORE_RENAME = [
        
        "auction_date",
        "ah_bp_price",
        "ah_price",
        "ah_price_usd",
        "ah_bp_price_usd",
    ]

    RENAME_MAP_NON_SOT = {
        "sale_number": "sale_id",
        "origin": "source",
        "diamond_ah_low_estimate": "ah_low_estimate",
        "diamond_ah_high_estimate": "ah_high_estimate",
        "diamond_ah_bp_price": "ah_bp_price",
        "hammer_price_original": "ah_price",
        "diamond_ah_low_estimate_usd": "ah_low_estimate_usd",
        "diamond_ah_high_estimate_usd": "ah_high_estimate_usd",
        "diamond_ah_price_usd": "ah_bp_price_usd",
        "hammer_price_usd": "ah_price_usd",   
    }

    # DROP RAW + NOISE AFTER RENAME
    DROP_COLS_NON_SOT = [
        "lot_status", "diamond_ah_bp_price", "hammer_price_original", "diamond_ah_price_usd", "hammer_price_usd"
    ]
    
    
    DROP_COLS_SOT = [
        "lot_status"
    ]

    def preprocess_non_sot(self, add_columns: dict | None = None):
        return (
            self.drop_columns(self.DROP_CANONICAL_BEFORE_RENAME)
                .rename_columns(self.RENAME_MAP_NON_SOT)
                .drop_columns(self.DROP_COLS_NON_SOT)
                .add_missing_columns(add_columns or {})
                .drop_na_required()
        )


    def preprocess_sot(self):
        return (
            self.drop_columns(self.DROP_COLS_SOT)
                .drop_na_required()
        )


def concat_same_schema(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_name: str = "left",
    right_name: str = "right",
) -> pd.DataFrame:
    cols_left = set(df_left.columns)
    cols_right = set(df_right.columns)

    # ---- schema check
    if cols_left != cols_right:
        missing_in_right = sorted(cols_left - cols_right)
        extra_in_right = sorted(cols_right - cols_left)

        print(f"\n❌ Schema mismatch between {left_name} and {right_name}")
        print(f"   Missing in {right_name}: {missing_in_right}")
        print(f"   Extra in {right_name}: {extra_in_right}")

        raise ValueError("Cannot concat: column sets do not match")

    # ---- duplicate column detection
    dup_left = df_left.columns[df_left.columns.duplicated()].tolist()
    dup_right = df_right.columns[df_right.columns.duplicated()].tolist()

    if dup_left or dup_right:
        print("\n❌ Duplicate columns detected")

        if dup_left:
            print(f"   {left_name} duplicates ({len(dup_left)}): {dup_left}")

        if dup_right:
            print(f"   {right_name} duplicates ({len(dup_right)}): {dup_right}")

        raise ValueError("Cannot concat: duplicate column names found")

    # ---- safe concat
    df_out = pd.concat([df_left, df_right], ignore_index=True)

    print(
        f"\n✅ Successfully merged {left_name} and {right_name}\n"
        f"   Final shape: {df_out.shape}"
    )

    return df_out

class SoTDataCleaner:
    """
    Post-preprocessing cleaner and QA utilities for auction datasets.
    """

    def __init__(self, df: pd.DataFrame, verbose: bool = True):
        self.df = df.copy()
        self.verbose = verbose
        self._step = 0

    # ---------- utils ----------
    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _next_step(self, title: str):
        self._step += 1
        self._log(f"\n[{self._step}] {title}")

    def _snapshot(self):
        return self.df.shape

    # ---------- cleaning steps ----------
    def drop_duplicate_lots(self, subset=("lot_url",)):
        self._next_step("Drop duplicate lots")

        before = self._snapshot()
        self.df = (
            self.df
            .drop_duplicates(subset=list(subset), keep="first")
            .reset_index(drop=True)
        )
        after = self._snapshot()

        self._log(f"  Rows: {before[0]} → {after[0]}")
        return self

    def drop_na_prices_and_dates(self):
        self._next_step("Drop rows with missing price or sale date")

        before = self._snapshot()
        self.df = self.df.dropna(subset=["ah_bp_price_usd", "sale_date"])
        after = self._snapshot()

        self._log(f"  Rows: {before[0]} → {after[0]}")
        return self

    def normalize_sale_date(self):
        self._next_step("Normalize sale_date and extract year")

        before = self._snapshot()

        self.df["sale_date"] = pd.to_datetime(
            self.df["sale_date"], errors="coerce"
        )
        self.df["year"] = self.df["sale_date"].dt.year

        after = self._snapshot()
        self._log(f"  Rows: {before[0]} → {after[0]} (no drops)")
        return self

    # ---------- reporting ----------
    def counts_by_year_and_house(self) -> pd.DataFrame:
        """
        Returns a wide table of counts by year and auction house.
        Does NOT modify df.
        """
        self._next_step("Counts by year and auction house")

        counts = (
            self.df
            .groupby(["year", "auction_house"])
            .size()
            .unstack(fill_value=0)
            .sort_index()
        )

        return counts

    def count_by_month_for_year(self, year: int) -> pd.DataFrame:
        """
        Count rows by month for a specific year.
        Does NOT modify the DataFrame.
        """
    
        self._next_step(f"Counts by month for year {year}")
    
        if "sale_date" not in self.df.columns:
            raise ValueError("sale_date column is required")
    
        # Ensure datetime
        sale_date = pd.to_datetime(self.df["sale_date"], errors="coerce")
    
        df_year = self.df[sale_date.dt.year == year].copy()
        df_year["month"] = sale_date.dt.month
    
        counts = (
            df_year
            .groupby("month")
            .size()
            .reindex(range(1, 13), fill_value=0)
        )
    
        self._log(f"  Total rows in {year}: {counts.sum()}")
    
        return counts.to_frame(name="count")


    # ---------- outlier handling ----------
    def flag_price_outliers(self, threshold: float = 1.5):
        self._next_step(f"Flag price outliers (threshold={threshold})")

        required = {
            "ah_bp_price_usd",
            "ah_low_estimate_usd",
            "ah_high_estimate_usd",
        }
        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"Missing columns for outlier detection: {missing}")

        before = self._snapshot()

        self.df["midpoint"] = (
            self.df["ah_low_estimate_usd"]
            + self.df["ah_high_estimate_usd"]
        ) / 2

        self.df["relative_diff"] = (
            self.df["ah_bp_price_usd"] - self.df["midpoint"]
        ).abs() / self.df["midpoint"]

        self.df["row_based_outlier"] = self.df["relative_diff"] > threshold

        num_outliers = int(self.df["row_based_outlier"].sum())
        self._log(f"  Outliers flagged: {num_outliers} / {before[0]}")

        return self

    def show_top_outliers(self, n: int = 10) -> pd.DataFrame:
        self._next_step(f"Show top {n} outliers")

        cols = [
            "ah_bp_price_usd",
            "ah_low_estimate_usd",
            "ah_high_estimate_usd",
            "relative_diff",
        ]

        return (
            self.df[self.df["row_based_outlier"]]
            .sort_values("relative_diff", ascending=False)[cols]
            .head(n)
        )

    def remove_outliers(self):
        self._next_step("Remove flagged outliers")

        before = self._snapshot()
        self.df = (
            self.df[~self.df["row_based_outlier"]]
            .reset_index(drop=True)
        )
        after = self._snapshot()

        self._log(f"  Rows: {before[0]} → {after[0]}")
        return self

    # ---------- final ----------
    def get_df(self) -> pd.DataFrame:
        return self.df

