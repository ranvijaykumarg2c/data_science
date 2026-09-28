"""Create static charts for the Memorabilia and cross-asset README."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


HERE = Path(__file__).resolve().parent
REPORT = HERE / "memorabilia_report"


def save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def main() -> None:
    REPORT.mkdir(exist_ok=True)

    estimates = pd.read_csv(REPORT / "estimate_summary.csv")
    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(
        estimates["estimate"],
        estimates["median_ape_pct"],
        color=["#4C78A8", "#F58518", "#E45756"],
    )
    plt.ylabel("Median absolute percentage error (%)")
    plt.title("Memorabilia: estimate-point error")
    for bar, value in zip(bars, estimates["median_ape_pct"]):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}%", ha="center")
    save(REPORT / "01_estimate_error.png")

    house = pd.read_csv(REPORT / "by_house.csv")
    plt.figure(figsize=(8, 4.5))
    bars = plt.bar(house["checked_house"], house["median_ape_pct"], color="#72B7B2")
    plt.ylabel("Median absolute percentage error (%)")
    plt.title("Memorabilia: midpoint error by auction house")
    plt.xticks(rotation=20, ha="right")
    for bar, value in zip(bars, house["median_ape_pct"]):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}%", ha="center")
    save(REPORT / "02_house_error.png")

    item_type = pd.read_csv(REPORT / "by_type.csv")
    plt.figure(figsize=(8, 4.5))
    bars = plt.bar(item_type["memorabilia_type"], item_type["median_ape_pct"], color="#54A24B")
    plt.ylabel("Median absolute percentage error (%)")
    plt.title("Memorabilia: midpoint error by type")
    plt.xticks(rotation=15, ha="right")
    for bar, value in zip(bars, item_type["median_ape_pct"]):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}%", ha="center")
    save(REPORT / "03_type_error.png")

    quarter = pd.read_csv(REPORT / "by_sale_quarter.csv")
    plt.figure(figsize=(8, 4.5))
    plt.plot(quarter["sale_quarter"], quarter["median_ape_pct"], marker="o", color="#B279A2")
    plt.ylabel("Median absolute percentage error (%)")
    plt.title("Memorabilia: midpoint error by sale quarter")
    plt.xticks(rotation=25, ha="right")
    plt.grid(axis="y", alpha=0.25)
    save(REPORT / "04_quarter_error.png")

    benchmark = pd.DataFrame(
        {
            "sample": ["Artwork", "Cars — Gooding", "Cars — RM Abu Dhabi", "Memorabilia"],
            "median_ape_pct": [34.98, 37.38, 11.11, 36.84],
            "within_20_pct": [29.98, 25.00, 86.96, 27.97],
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    axes[0].bar(benchmark["sample"], benchmark["median_ape_pct"], color="#4C78A8")
    axes[0].set_ylabel("Median absolute percentage error (%)")
    axes[0].set_title("Midpoint error")
    axes[0].tick_params(axis="x", rotation=25)
    axes[1].bar(benchmark["sample"], benchmark["within_20_pct"], color="#F58518")
    axes[1].set_ylabel("Within ±20% of result (%)")
    axes[1].set_title("Midpoint threshold accuracy")
    axes[1].tick_params(axis="x", rotation=25)
    save(REPORT / "05_cross_asset_benchmark.png")


if __name__ == "__main__":
    main()
