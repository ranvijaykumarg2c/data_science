# Auction Estimate Accuracy Analysis

This project benchmarks auction-house estimates against recorded sale results for Artwork, Cars, and Memorabilia. It includes cleaned analysis tables, reproducible report scripts, and PNG charts. The detailed report documents matching rules, data-quality decisions, segment results, and limitations.

## Headline results

| Asset or event | Matched lots | Midpoint median absolute percentage error |
|---|---:|---:|
| Artwork | 29,095 | 34.98% |
| Cars: Gooding Amelia Island 2025 | 128 | 37.38% |
| Cars: RM Abu Dhabi 2025 | 23 | 11.11% |
| Memorabilia | 2,360 | 36.84% |

The low estimate had a lower median absolute percentage error than the midpoint in each analyzed sample. These are auction-house estimate benchmarks, not Barkr or local-pricer results: item-level predictions for those methods were not included. The Cars figures use inferred hammer prices and cover only two events; the RM result is based on 23 cars.

## Visual results

### Cross-asset benchmark

![Midpoint error and within-20-percent accuracy by asset or event](daily_sales/memorabilia_report/05_cross_asset_benchmark.png)

### Artwork

![Artwork hammer-price distribution](daily_sales/artwork_report/01_hammer_distribution.png)

![Artwork actual price versus estimate midpoint](daily_sales/artwork_report/02_actual_vs_midpoint.png)

![Artwork result position relative to estimate range](daily_sales/artwork_report/03_range_position.png)

![Artwork midpoint error by auction house](daily_sales/artwork_report/04_house_error.png)

![Artwork error by estimated value band](daily_sales/artwork_report/05_estimated_value_error.png)

![Artwork error by sale quarter](daily_sales/artwork_report/06_quarter_error.png)

### Cars

![Cars estimate error by event](daily_sales/cars_report/01_estimate_error_by_event.png)

![Cars inferred hammer position relative to estimate range](daily_sales/cars_report/02_range_position_by_event.png)

### Memorabilia

![Memorabilia error by estimate point](daily_sales/memorabilia_report/01_estimate_error.png)

![Memorabilia midpoint error by auction house](daily_sales/memorabilia_report/02_house_error.png)

![Memorabilia midpoint error by item type](daily_sales/memorabilia_report/03_type_error.png)

![Memorabilia midpoint error by sale quarter](daily_sales/memorabilia_report/04_quarter_error.png)

## Contents

- [Detailed analysis and methodology](daily_sales/README.md)
- [Artwork report outputs and script](daily_sales/artwork_report/)
- [Cars report outputs and script](daily_sales/cars_report/)
- [Memorabilia report outputs and scripts](daily_sales/memorabilia_report/)
- [Daily-sales source exports](daily_sales/)

The three current source JSON exports are tracked with [Git LFS](https://git-lfs.com/). `Data/OutputOld/` is a local legacy archive and is intentionally excluded from this repository; `.venv/` and Python-generated cache files are excluded as well.