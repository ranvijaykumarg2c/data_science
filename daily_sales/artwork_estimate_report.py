"""Build the Artwork auction-estimate analysis from the daily-sales export.

This deliberately analyzes auction-house estimates only. The daily-sales export
does not contain Barkr, Local Pricer, Standard, or Llama predictions.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "artwork_daily_sale.json"
OUT = ROOT / "artwork_report"
NUMERIC = [
    "ah_price",
    "ah_bp_price",
    "ah_low_estimate",
    "ah_high_estimate",
    "ah_price_usd",
    "ah_bp_price_usd",
    "ah_low_estimate_usd",
    "ah_high_estimate_usd",
]


def save_plot(name: str) -> None:
    plt.tight_layout()
    plt.savefig(OUT / name, dpi=170, bbox_inches="tight")
    plt.close()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    raw = pd.read_json(SOURCE)
    raw[NUMERIC] = raw[NUMERIC].astype("string").replace(",", "", regex=True).apply(
        pd.to_numeric, errors="coerce"
    )

    grouped = raw.groupby("lot_url")
    conflict = (
        grouped["auction_house"].nunique().gt(1)
        | grouped["ah_price"].nunique(dropna=True).gt(1)
        | grouped["ah_low_estimate"].nunique(dropna=True).gt(1)
        | grouped["ah_high_estimate"].nunique(dropna=True).gt(1)
    )
    conflict_urls = conflict[conflict].index
    raw[raw["lot_url"].isin(conflict_urls)].to_csv(
        OUT / "excluded_conflicting_urls.csv", index=False
    )

    lots = raw[~raw["lot_url"].isin(conflict_urls)].copy()
    lots["complete"] = lots[NUMERIC].notna().sum(axis=1)
    lots = lots.sort_values("complete", kind="stable").drop_duplicates(
        "lot_url", keep="last"
    )
    lots["positive_hammer"] = lots["ah_price"].fillna(0).gt(0)
    lots["valid_estimate"] = (
        lots["ah_low_estimate"].fillna(0).gt(0)
        & lots["ah_high_estimate"].fillna(0).gt(0)
        & lots["ah_low_estimate"].le(lots["ah_high_estimate"]).fillna(False)
    )
    lots["status_group"] = lots["lot_status"].fillna("missing")
    lots.to_csv(OUT / "canonical_lots.csv", index=False)

    q = lots[lots["positive_hammer"] & lots["valid_estimate"]].copy()
    q["midpoint"] = (q["ah_low_estimate"] + q["ah_high_estimate"]) / 2
    q["midpoint_usd"] = (
        q["ah_low_estimate_usd"] + q["ah_high_estimate_usd"]
    ) / 2
    q["signed_error_pct"] = (q["midpoint"] / q["ah_price"] - 1) * 100
    q["ape_pct"] = q["signed_error_pct"].abs()
    q["abs_error_usd"] = (q["midpoint_usd"] - q["ah_price_usd"]).abs()
    q["position"] = np.select(
        [q["ah_price"].lt(q["ah_low_estimate"]), q["ah_price"].gt(q["ah_high_estimate"])],
        ["below", "above"],
        default="within",
    )
    q["medium_clean"] = (
        q["medium"].fillna("missing").astype(str).str.strip().str.lower().replace("", "missing")
    )
    q["sale_date_parsed"] = pd.to_datetime(q["sale_date"], errors="coerce")
    q.to_csv(OUT / "analysis_lots.csv", index=False)

    rows = []
    for label, native, usd in [
        ("Low estimate", "ah_low_estimate", "ah_low_estimate_usd"),
        ("Estimate midpoint", "midpoint", "midpoint_usd"),
        ("High estimate", "ah_high_estimate", "ah_high_estimate_usd"),
    ]:
        error = (q[native] / q["ah_price"] - 1) * 100
        usd_error = q[usd] - q["ah_price_usd"]
        rows.append(
            {
                "comparison": label,
                "N": len(q),
                "median_ape_pct": error.abs().median(),
                "median_bias_pct": error.median(),
                "median_abs_error_usd": usd_error.abs().median(),
                "median_signed_error_usd": usd_error.median(),
                "within_10_pct": error.abs().le(10).mean() * 100,
                "within_20_pct": error.abs().le(20).mean() * 100,
                "within_30_pct": error.abs().le(30).mean() * 100,
            }
        )
    summary = pd.DataFrame(rows).round(2)
    summary.to_csv(OUT / "estimate_summary.csv", index=False)

    position = q["position"].value_counts().reindex(["below", "within", "above"], fill_value=0)
    position.rename_axis("position").reset_index(name="N").assign(
        pct=lambda frame: (frame["N"] / len(q) * 100).round(2)
    ).to_csv(OUT / "range_position.csv", index=False)

    q["within_20"] = q["ape_pct"].le(20) * 100
    house = q.groupby("auction_house").agg(
        N=("ape_pct", "size"),
        median_ape_pct=("ape_pct", "median"),
        within_20_pct=("within_20", "mean"),
        median_hammer_usd=("ah_price_usd", "median"),
    )
    house["usable_share_pct"] = house["N"] / lots.groupby("auction_house").size() * 100
    house.round(2).sort_values("median_ape_pct").to_csv(OUT / "house_summary.csv")

    q["estimated_value_band"] = pd.qcut(q["midpoint_usd"], 4, duplicates="drop")
    bands = q.groupby("estimated_value_band", observed=True).agg(
        N=("ape_pct", "size"), median_ape_pct=("ape_pct", "median")
    )
    bands.round(2).to_csv(OUT / "estimated_value_bands.csv")

    medium = q.groupby("medium_clean").agg(
        N=("ape_pct", "size"), median_ape_pct=("ape_pct", "median")
    )
    medium.round(2).sort_values("N", ascending=False).to_csv(OUT / "medium_summary.csv")

    dated = q[q["sale_date_parsed"].notna()].copy()
    dated["quarter"] = dated["sale_date_parsed"].dt.to_period("Q").astype(str)
    quarter = dated.groupby("quarter").agg(
        N=("ape_pct", "size"), median_ape_pct=("ape_pct", "median")
    )
    quarter.round(2).to_csv(OUT / "quarter_summary.csv")

    quality = pd.Series(
        {
            "raw_rows": len(raw),
            "conflicting_urls": len(conflict_urls),
            "unique_lots_retained": len(lots),
            "positive_hammer_lots": int(lots["positive_hammer"].sum()),
            "valid_estimate_lots": int(lots["valid_estimate"].sum()),
            "analysis_lots": len(q),
            "analysis_lots_missing_date": int(q["sale_date_parsed"].isna().sum()),
            "explicitly_sold": int(lots["status_group"].eq("sold").sum()),
            "explicitly_unsold": int(lots["status_group"].eq("unsold").sum()),
            "status_missing": int(lots["status_group"].eq("missing").sum()),
        },
        name="value",
    )
    quality.rename_axis("measure").to_csv(OUT / "data_quality.csv")

    # Charts use the same canonical 29,095-lot sample as the summary tables.
    plt.figure(figsize=(8, 4.7))
    plt.hist(np.log10(q["ah_price_usd"].astype(float)), bins=55, color="#426b9b")
    plt.xlabel("Actual hammer price, log10 USD")
    plt.ylabel("Lots")
    plt.title("Artwork hammer prices")
    save_plot("01_hammer_distribution.png")

    sample = q.sample(min(9000, len(q)), random_state=42)
    plt.figure(figsize=(6.4, 6.4))
    plt.scatter(sample["ah_price_usd"].astype(float), sample["midpoint_usd"].astype(float),
                s=5, alpha=0.18, color="#426b9b")
    limits = [max(1, min(q["ah_price_usd"].min(), q["midpoint_usd"].min())),
              max(q["ah_price_usd"].max(), q["midpoint_usd"].max())]
    plt.plot(limits, limits, color="#bd522b", linewidth=1.5)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlim(limits)
    plt.ylim(limits)
    plt.xlabel("Actual hammer, USD")
    plt.ylabel("Estimate midpoint, USD")
    plt.title("Actual versus auction estimate midpoint")
    save_plot("02_actual_vs_midpoint.png")

    plt.figure(figsize=(6.5, 4.5))
    bars = plt.bar(position.index, position.values / len(q) * 100,
                   color=["#bd522b", "#426b9b", "#5c8a65"])
    plt.bar_label(bars, fmt="%.1f%%")
    plt.ylabel("Lots (%)")
    plt.title("Hammer price versus published estimate range")
    save_plot("03_range_position.png")

    house_plot = house.sort_values("median_ape_pct")
    plt.figure(figsize=(8, 4.8))
    plt.barh(house_plot.index, house_plot["median_ape_pct"], color="#426b9b")
    plt.gca().invert_yaxis()
    plt.xlabel("Median absolute percentage error (%)")
    plt.title("Estimate midpoint error by auction house")
    save_plot("04_house_error.png")

    plt.figure(figsize=(7, 4.5))
    plt.bar(["Q1", "Q2", "Q3", "Q4"][: len(bands)], bands["median_ape_pct"], color="#426b9b")
    plt.xlabel("Estimate midpoint USD quartile, low to high")
    plt.ylabel("Median absolute percentage error (%)")
    plt.title("Error by pre-sale estimated value")
    save_plot("05_estimated_value_error.png")

    plt.figure(figsize=(9, 4.8))
    plt.plot(quarter.index, quarter["median_ape_pct"], marker="o", color="#426b9b")
    plt.xticks(rotation=45)
    plt.ylabel("Median absolute percentage error (%)")
    plt.title("Estimate midpoint error by sale quarter")
    save_plot("06_quarter_error.png")

    print(f"Source rows: {len(raw):,}; unique lots: {len(lots):,}; analysis lots: {len(q):,}")
    print(summary.to_string(index=False))
    print(f"Saved tables and six charts to {OUT}")


if __name__ == "__main__":
    main()
