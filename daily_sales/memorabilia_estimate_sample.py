"""Build a reusable lot-level sample for Memorabilia estimate comparisons."""

from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "Memorabilia_daily_sale.json"
OUTPUT = HERE / "memorabilia_estimate_sample.csv"


def main() -> None:
    data = pd.read_json(SOURCE)
    numeric = [
        "ah_price",
        "ah_bp_price",
        "ah_price_usd",
        "ah_bp_price_usd",
        "ah_low_estimate",
        "ah_high_estimate",
        "ah_low_estimate_usd",
        "ah_high_estimate_usd",
    ]
    numeric = [column for column in numeric if column in data]
    for column in numeric:
        data[column] = pd.to_numeric(
            data[column].astype("string").str.replace(",", "", regex=False),
            errors="coerce",
        )

    data["checked_currency"] = data["currency"].astype("string")
    sale = data["auction_url"].fillna("").astype(str)
    missing_christies = data["checked_currency"].isna() & data["auction_house"].eq(
        "Christies"
    )
    data.loc[
        missing_christies & sale.str.contains("the-jim-irsay-collection", case=False),
        "checked_currency",
    ] = "USD"
    data.loc[
        missing_christies & sale.str.contains("groundbreakers-icons", case=False),
        "checked_currency",
    ] = "GBP"
    data["currency_inferred"] = data["currency"].isna() & data[
        "checked_currency"
    ].notna()

    data["checked_house"] = data["auction_house"].astype("string")
    url = data["lot_url"].fillna("").astype(str)
    data.loc[url.str.contains("freemansauction.com", case=False), "checked_house"] = (
        "Freemans"
    )
    data.loc[url.str.contains("sothebys.com", case=False), "checked_house"] = (
        "Sothebys"
    )

    grouped = data.groupby("lot_url", sort=False)
    lots = grouped[numeric].max()
    for column in [
        "checked_currency",
        "checked_house",
        "memorabilia_type",
        "sport",
        "title",
        "sale_date",
        "auction_url",
    ]:
        lots[column] = grouped[column].first()
    lots["currency_inferred"] = grouped["currency_inferred"].any()
    lots["source_rows"] = grouped.size()

    valid = (
        lots["ah_price"].gt(0)
        & lots["ah_low_estimate"].gt(0)
        & lots["ah_high_estimate"].gt(0)
        & lots["ah_low_estimate"].le(lots["ah_high_estimate"])
        & lots["checked_currency"].notna()
    )
    sample = lots.loc[valid].copy()
    midpoint = (sample["ah_low_estimate"] + sample["ah_high_estimate"]) / 2
    sample["midpoint_ape_pct"] = (
        100 * (midpoint - sample["ah_price"]).abs() / sample["ah_price"]
    )
    sample["midpoint_bias_pct"] = (
        100 * (midpoint - sample["ah_price"]) / sample["ah_price"]
    )
    sample.to_csv(OUTPUT, index=True)
    print(f"Saved {len(sample)} unique matched lots to {OUTPUT}")
    print(f"Currency inferred for {sample['currency_inferred'].sum()} matched lots")


if __name__ == "__main__":
    main()
