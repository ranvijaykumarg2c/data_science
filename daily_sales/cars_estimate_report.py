"""Rebuild the limited Cars auction-estimate comparison from daily sales.

Gooding Amelia Island 2025 and RM Sotheby's Abu Dhabi 2025 are analyzed
separately. Published sold prices are converted to inferred hammer prices using
each event's published buyer-premium schedule. Paris is excluded pending
price-basis review. No Barkr or Local Pricer outputs are present in this export.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cars_report"
SOURCE = ROOT / "Cars_daily_sale.json"
PRICE_COLUMNS = ["ah_price", "ah_low_estimate", "ah_high_estimate"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    raw = pd.read_json(SOURCE)
    raw[PRICE_COLUMNS] = (
        raw[PRICE_COLUMNS]
        .astype("string")
        .replace(",", "", regex=True)
        .apply(pd.to_numeric, errors="coerce")
    )
    grouped = raw.groupby("lot_url")
    price_conflicts = grouped["ah_price"].nunique(dropna=True).gt(1)
    lots = grouped[PRICE_COLUMNS].max()
    lots["source"] = [
        "Gooding Amelia Island 2025"
        if "goodingco.com" in url
        else "RM Abu Dhabi 2025"
        if "/auctions/ad25/" in url
        else "RM Paris 2026"
        if "/auctions/pa26/" in url
        else "Other"
        for url in lots.index
    ]
    valid = (
        lots["ah_price"].fillna(0).gt(0)
        & lots["ah_low_estimate"].fillna(0).gt(0)
        & lots["ah_high_estimate"].fillna(0).gt(0)
        & lots["ah_low_estimate"].le(lots["ah_high_estimate"]).fillna(False)
    )
    matched = lots[valid & ~lots.index.isin(price_conflicts[price_conflicts].index)].copy()
    matched.to_csv(OUT / "matched_lots_before_basis_check.csv")
    q = matched[matched["source"].isin(["Gooding Amelia Island 2025", "RM Abu Dhabi 2025"])].copy()
    q["inferred_hammer"] = np.nan
    gooding = q["source"].eq("Gooding Amelia Island 2025")
    abu = q["source"].eq("RM Abu Dhabi 2025")
    gooding_price = q.loc[gooding, "ah_price"].astype(float)
    abu_price = q.loc[abu, "ah_price"].astype(float)
    # Gooding: 12% through $250k hammer; 10% above. Sold-price pivot is $280k.
    q.loc[gooding, "inferred_hammer"] = np.where(
        gooding_price <= 280_000,
        gooding_price / 1.12,
        (gooding_price - 5_000) / 1.10,
    )
    # RM Abu Dhabi: 15% through $200k hammer; 12.5% above.
    # Sold-price pivot is $230k. Published result appears to exclude VAT.
    q.loc[abu, "inferred_hammer"] = np.where(
        abu_price <= 230_000,
        abu_price / 1.15,
        (abu_price - 5_000) / 1.125,
    )
    q["round_100_bid"] = (
        (q["inferred_hammer"] / 100).round() * 100 - q["inferred_hammer"]
    ).abs().le(1)
    basis_anomalies = q[gooding & ~q["round_100_bid"]].copy()
    basis_anomalies.to_csv(OUT / "gooding_basis_anomalies.csv")
    q = q[~(gooding & ~q["round_100_bid"])].copy()
    gooding = q["source"].eq("Gooding Amelia Island 2025")
    abu = q["source"].eq("RM Abu Dhabi 2025")
    q["midpoint"] = (q["ah_low_estimate"] + q["ah_high_estimate"]) / 2
    q["signed_error_pct"] = (q["midpoint"] / q["inferred_hammer"] - 1) * 100
    q["ape_pct"] = q["signed_error_pct"].abs()
    q["abs_error_usd"] = (q["midpoint"] - q["inferred_hammer"]).abs()
    q["position"] = np.select(
        [q["inferred_hammer"].lt(q["ah_low_estimate"]),
         q["inferred_hammer"].gt(q["ah_high_estimate"])],
        ["below", "above"], default="within"
    )
    q.to_csv(OUT / "analysis_lots.csv")

    summary_rows = []
    for source, subset in q.groupby("source"):
        for label, column in [
            ("Low", "ah_low_estimate"),
            ("Midpoint", "midpoint"),
            ("High", "ah_high_estimate"),
        ]:
            error = (subset[column] / subset["inferred_hammer"] - 1) * 100
            summary_rows.append(
                {
                    "source": source,
                    "estimate": label,
                    "N": len(subset),
                    "median_hammer_usd": subset["inferred_hammer"].median(),
                    "median_ape_pct": error.abs().median(),
                    "median_bias_pct": error.median(),
                    "median_abs_error_usd": (subset[column] - subset["inferred_hammer"]).abs().median(),
                    "within_10_pct": error.abs().le(10).mean() * 100,
                    "within_20_pct": error.abs().le(20).mean() * 100,
                    "within_30_pct": error.abs().le(30).mean() * 100,
                    "below_range_pct": subset["position"].eq("below").mean() * 100,
                    "within_range_pct": subset["position"].eq("within").mean() * 100,
                    "above_range_pct": subset["position"].eq("above").mean() * 100,
                }
            )
    summary = pd.DataFrame(summary_rows).round(2)
    summary.to_csv(OUT / "estimate_summary.csv", index=False)

    pd.Series(
        {
            "raw_rows": len(raw),
            "distinct_lot_urls": raw["lot_url"].nunique(),
            "duplicate_url_rows": int(raw["lot_url"].duplicated().sum()),
            "price_conflict_urls": int(price_conflicts.sum()),
            "rows_missing_auction_house": int(raw["auction_house"].isna().sum()),
            "rows_missing_sale_date": int(raw["sale_date"].isna().sum()),
            "matched_lots_before_basis_check": len(matched),
            "paris_matched_excluded": int(matched["source"].eq("RM Paris 2026").sum()),
            "gooding_basis_anomalies_excluded": len(basis_anomalies),
            "analysis_lots": len(q),
            "gooding_round_bid_check": int(q.loc[gooding, "round_100_bid"].sum()),
            "abu_dhabi_round_bid_check": int(q.loc[abu, "round_100_bid"].sum()),
        }, name="value"
    ).rename_axis("measure").to_csv(OUT / "data_quality.csv")

    q.nlargest(20, "ape_pct").to_csv(OUT / "top_percentage_misses.csv")
    q.nlargest(20, "abs_error_usd").to_csv(OUT / "top_dollar_misses.csv")

    pivot = summary.pivot(index="source", columns="estimate", values="median_ape_pct")
    pivot = pivot[["Low", "Midpoint", "High"]]
    ax = pivot.plot.bar(figsize=(8, 4.8), color=["#4b729b", "#c48b4f", "#5c8a65"])
    ax.set_ylabel("Median absolute percentage error (%)")
    ax.set_xlabel("")
    ax.set_title("Cars: estimate error by auction event")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(OUT / "01_estimate_error_by_event.png", dpi=170, bbox_inches="tight")
    plt.close()

    positions = pd.crosstab(q["source"], q["position"], normalize="index") * 100
    positions = positions.reindex(columns=["below", "within", "above"], fill_value=0)
    ax = positions.plot.bar(stacked=True, figsize=(8, 4.8),
                            color=["#bd522b", "#426b9b", "#5c8a65"])
    ax.set_ylabel("Lots (%)")
    ax.set_xlabel("")
    ax.set_title("Cars: inferred hammer versus estimate range")
    ax.legend(title="Position")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(OUT / "02_range_position_by_event.png", dpi=170, bbox_inches="tight")
    plt.close()

    print(f"Raw rows: {len(raw):,}; matched lots: {len(matched):,}; analyzed: {len(q):,}")
    print(summary[summary["estimate"].eq("Midpoint")].to_string(index=False))
    print(f"Saved tables and charts to {OUT}")


if __name__ == "__main__":
    main()
