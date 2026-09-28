"""Write reproducible Memorabilia auction-estimate tables and outlier lists."""

from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
OUT = HERE / "memorabilia_report"
SAMPLE = HERE / "memorabilia_estimate_sample.csv"
RAW = HERE / "Memorabilia_daily_sale.json"


def summary(frame: pd.DataFrame, prediction: pd.Series) -> dict:
    actual = frame["ah_price"]
    signed = 100 * (prediction - actual) / actual
    absolute = signed.abs()
    return {
        "N": len(frame),
        "median_ape_pct": absolute.median(),
        "median_bias_pct": signed.median(),
        "within_10_pct": 100 * absolute.le(10).mean(),
        "within_20_pct": 100 * absolute.le(20).mean(),
        "within_30_pct": 100 * absolute.le(30).mean(),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    x = pd.read_csv(SAMPLE)
    midpoint = (x.ah_low_estimate + x.ah_high_estimate) / 2

    estimates = pd.DataFrame.from_dict(
        {
            "Low": summary(x, x.ah_low_estimate),
            "Midpoint": summary(x, midpoint),
            "High": summary(x, x.ah_high_estimate),
        },
        orient="index",
    ).round(2)
    estimates.index.name = "estimate"
    estimates.to_csv(OUT / "estimate_summary.csv")

    x["below_range"] = x.ah_price.lt(x.ah_low_estimate)
    x["in_range"] = x.ah_price.between(x.ah_low_estimate, x.ah_high_estimate)
    x["above_range"] = x.ah_price.gt(x.ah_high_estimate)
    x["within_20"] = x.midpoint_ape_pct.le(20)
    x["midpoint"] = midpoint

    def segment(keys: list[str], filename: str) -> pd.DataFrame:
        result = x.groupby(keys, dropna=False).agg(
            N=("midpoint_ape_pct", "size"),
            median_ape_pct=("midpoint_ape_pct", "median"),
            median_bias_pct=("midpoint_bias_pct", "median"),
            within_20_pct=("within_20", "mean"),
            below_range_pct=("below_range", "mean"),
            in_range_pct=("in_range", "mean"),
            above_range_pct=("above_range", "mean"),
        )
        for column in ["within_20_pct", "below_range_pct", "in_range_pct", "above_range_pct"]:
            result[column] *= 100
        result = result.round(2)
        result.to_csv(OUT / filename)
        return result

    by_house = segment(["checked_house"], "by_house.csv")
    by_type = segment(["memorabilia_type"], "by_type.csv")
    segment(["memorabilia_type", "checked_house"], "by_type_and_house.csv")
    segment(["sport", "checked_house"], "by_sport_and_house.csv")

    x["sale_date_parsed"] = pd.to_datetime(x.sale_date, errors="coerce")
    dated = x[x.sale_date_parsed.notna()].copy()
    dated["sale_quarter"] = dated.sale_date_parsed.dt.to_period("Q").astype(str)
    quarterly = dated.groupby("sale_quarter").agg(
        N=("midpoint_ape_pct", "size"),
        median_ape_pct=("midpoint_ape_pct", "median"),
        within_20_pct=("within_20", "mean"),
    )
    quarterly["within_20_pct"] *= 100
    quarterly.round(2).to_csv(OUT / "by_sale_quarter.csv")

    # Value bands use the published pre-sale midpoint in USD for USD lots only.
    usd = x[x.checked_currency.eq("USD")].copy()
    usd["estimate_band_usd"] = pd.qcut(
        usd.midpoint, q=4, duplicates="drop", precision=2
    ).astype(str)
    bands = usd.groupby("estimate_band_usd").agg(
        N=("midpoint_ape_pct", "size"),
        median_ape_pct=("midpoint_ape_pct", "median"),
        median_bias_pct=("midpoint_bias_pct", "median"),
        within_20_pct=("within_20", "mean"),
    )
    bands["within_20_pct"] *= 100
    bands.round(2).to_csv(OUT / "by_estimate_band_usd.csv")
    band_house = usd.groupby(["estimate_band_usd", "checked_house"]).agg(
        N=("midpoint_ape_pct", "size"),
        median_ape_pct=("midpoint_ape_pct", "median"),
    )
    band_house.round(2).to_csv(OUT / "by_band_and_house_usd.csv")

    # For native USD lots, amounts are already dollars. For GBP lots, use the
    # export's USD fields only when actual and both estimate values are present.
    x["actual_usd"] = x.ah_price_usd.where(x.checked_currency.ne("USD"), x.ah_price)
    x["low_usd"] = x.ah_low_estimate_usd.where(
        x.checked_currency.ne("USD"), x.ah_low_estimate
    )
    x["high_usd"] = x.ah_high_estimate_usd.where(
        x.checked_currency.ne("USD"), x.ah_high_estimate
    )
    usd_ok = (
        x.actual_usd.gt(0) & x.low_usd.gt(0) & x.high_usd.gt(0)
    )
    usd_error = (x.loc[usd_ok, ["low_usd", "high_usd"]].mean(axis=1) - x.loc[usd_ok, "actual_usd"])
    x["midpoint_abs_usd_error"] = pd.NA
    x.loc[usd_ok, "midpoint_abs_usd_error"] = usd_error.abs()
    dollar_summary = pd.DataFrame(
        [{
            "N": int(usd_ok.sum()),
            "median_abs_usd_error": usd_error.abs().median(),
            "median_signed_usd_error": usd_error.median(),
        }]
    ).round(2)
    dollar_summary.to_csv(OUT / "dollar_error_summary.csv", index=False)

    columns = [
        "lot_url", "title", "checked_house", "memorabilia_type", "sport",
        "checked_currency", "ah_price", "ah_low_estimate", "ah_high_estimate",
        "midpoint", "midpoint_ape_pct", "midpoint_bias_pct",
    ]
    x.nlargest(25, "midpoint_bias_pct")[columns].to_csv(
        OUT / "largest_overestimates_pct.csv", index=False
    )
    x.nsmallest(25, "midpoint_bias_pct")[columns].to_csv(
        OUT / "largest_underestimates_pct.csv", index=False
    )
    x.loc[usd_ok].sort_values(
        "midpoint_abs_usd_error", ascending=False
    ).head(25)[columns + ["midpoint_abs_usd_error"]].to_csv(
        OUT / "largest_usd_misses.csv", index=False
    )

    raw = pd.read_json(RAW)
    raw["checked_house"] = raw.auction_house.astype("string")
    urls = raw.lot_url.fillna("").astype(str)
    raw.loc[urls.str.contains("freemansauction.com", case=False), "checked_house"] = "Freemans"
    raw.loc[urls.str.contains("sothebys.com", case=False), "checked_house"] = "Sothebys"
    unique_by_house = raw.groupby("checked_house").lot_url.nunique()
    coverage = by_house[["N"]].copy()
    coverage["unique_exported_lots"] = unique_by_house
    coverage["sample_share_pct"] = 100 * coverage.N / coverage.unique_exported_lots
    coverage.round(2).to_csv(OUT / "coverage_by_house.csv")

    print("Baseline estimates:\n", estimates.to_string())
    print("\nBy house:\n", by_house.to_string())
    print("\nBy type:\n", by_type.to_string())
    print("\nDollar error:\n", dollar_summary.to_string(index=False))
    print("\nNo valid sale date:", len(x) - len(dated))
    print("Report tables written to", OUT)


if __name__ == "__main__":
    main()
