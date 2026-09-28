# Auction Estimate Accuracy Analysis

This report compares auction-house estimates with recorded results for Artwork, Cars, and Memorabilia. It describes the samples, matching and price-basis decisions, the main accuracy results, and what each saved chart shows. The source exports are dated 25 September 2026.

## Executive Summary

The three exports contain **50,008 raw rows**: 43,530 Artwork, 1,666 Cars, and 4,812 Memorabilia. After matching usable sale results to valid estimate ranges, the analysis covers 29,095 Artwork lots, 151 Cars from two events, and 2,360 Memorabilia lots.

| Sample | Matched lots | Midpoint median absolute percentage error | Midpoint within +/-20% |
|---|---:|---:|---:|
| Artwork | 29,095 | 34.98% | 29.98% |
| Cars: Gooding Amelia Island 2025 | 128 | 37.38% | 25.00% |
| Cars: RM Abu Dhabi 2025 | 23 | 11.11% | 86.96% |
| Memorabilia | 2,360 | 36.84% | 27.97% |

The published low estimate has a lower median absolute percentage error than the midpoint in every analyzed asset/event sample. That is a descriptive benchmark, not evidence that the low estimate is a better pricing model. RM Abu Dhabi has only 23 matched cars, Cars coverage overall is low, and each asset has different sample composition.

These results measure auction-house estimates only. No item-level Barkr, Local Pricer, Standard, or Llama predictions were supplied, so this analysis cannot rank those methods or measure their improvement over auction estimates.

## Scope and Method

| Asset | Raw rows | Distinct lots after cleaning | Comparison sample | Share of distinct lots | Comparison basis |
|---|---:|---:|---:|---:|---|
| Artwork | 43,530 | 39,976 | 29,095 | 72.78% | Positive `ah_price`; valid low/high estimates; native currency |
| Cars | 1,666 | 1,412 | 151 | 10.69% | USD events; buyer-premium-inclusive result inverted to inferred hammer |
| Memorabilia | 4,812 | 4,782 | 2,360 | 49.35% | Positive `ah_price`; valid estimates; observed or inferred currency |

The unit of analysis is a lot URL, not a row or display ID. A lot is included in percentage-error calculations only when its actual result is positive, both estimates are positive, the low estimate does not exceed the high estimate, and the currency is comparable. Missing results are not treated as zero. The midpoint is the arithmetic mean of the low and high estimate.

Signed percentage error is `(estimate - actual) / actual * 100`; a positive value means the estimate is above the result. Absolute percentage error removes direction. The headline error is the **median** absolute percentage error, which is less sensitive to extreme lots than a mean. Threshold accuracy is the share whose absolute percentage error is within 10%, 20%, or 30%.

Artwork and Memorabilia use native-currency values for percentage errors. Their dollar-error calculations use comparable USD values only. Cars auction estimates exclude the buyer's premium, while published sold amounts appear to include it; the relevant event premium schedule was inverted to estimate the hammer. Those Cars hammers are calculated, not observed hammer fields.

### Data-quality decisions

- Artwork has 3,420 duplicate-URL rows and conflicting records. The analysis excludes 134 URLs with conflicting house, price, or estimate fields, then retains one most-complete row per remaining URL. `ah_price` is treated as a pre-premium/hammer proxy, subject to confirmation from the data owner.
- Cars has 254 duplicate-URL rows, seven URLs with conflicting sold prices, and substantial missing house/date fields. The RM Paris match is excluded because its dates and EUR price basis are unresolved. Four Gooding lots are excluded because premium inversion does not produce a plausible round bid. The final event samples are 128 Gooding and 23 RM Abu Dhabi lots.
- Memorabilia has 30 repeated URLs without conflicting values. The analysis corrects 715 `Unknown Marketplace` rows to Freemans based on their URLs. Currency is inferred for 247 matched Christie's lots: 221 Jim Irsay lots as USD and 26 Groundbreakers lots as GBP. These inferred currencies should be verified.
- Artwork and Memorabilia `ah_price`/`ah_bp_price` ratios support, but do not prove, that the former is pre-premium and the latter premium-inclusive. Some Memorabilia prices are decimal equivalents rather than literal bid amounts.

## Artwork Results

The Artwork sample includes 29,095 of 39,976 retained unique lots. The midpoint median absolute percentage error is **34.98%**, the median signed error is **+4.17%**, and the median absolute USD error is **$3,525**. The result falls below, within, and above the published estimate range for **31.52%, 32.45%, and 36.03%** of lots, respectively.

| Estimate point | Median absolute % error | Median signed % error | Within +/-10% | Within +/-20% | Within +/-30% |
|---|---:|---:|---:|---:|---:|
| Low | 33.55% | -16.29% | 19.10% | 34.22% | 45.99% |
| Midpoint | 34.98% | +4.17% | 13.45% | 29.98% | 42.79% |
| High | 41.73% | +25.00% | 11.10% | 23.43% | 35.15% |

The low estimate has the lowest median absolute error, but its negative signed error shows it tends to sit below the realized hammer. The high estimate has the largest error and positive bias.

| Auction house | N | Midpoint median absolute % error | Within +/-20% | Median hammer (USD) |
|---|---:|---:|---:|---:|
| Phillips | 3,322 | 32.35% | 32.24% | $7,572 |
| Bonhams | 5,283 | 33.33% | 31.40% | $3,291 |
| Sotheby's | 7,719 | 34.98% | 30.57% | $20,833 |
| Christie's | 10,669 | 35.58% | 29.19% | $21,432 |
| Freemans | 417 | 41.18% | 25.18% | $2,750 |
| Hindman | 1,685 | 44.67% | 24.51% | $2,400 |

Phillips has the lowest observed house-level midpoint error and Hindman the highest, but their lot values, media, and eligibility rates differ. This table is descriptive, not a controlled house ranking. By medium, midpoint error is lowest among prints (33.04%, N=5,076) and paintings (33.55%, N=10,292), and highest among furniture (49.80%, N=745). Other substantial groups include photographs (40.63%, N=2,177), decorative arts (40.94%, N=1,616), and ceramics (40.34%, N=1,151).

Using the **pre-sale estimated USD midpoint** to create value bands, midpoint error declines from 44.21% for lots up to $3,500 (N=7,302) to 27.32% above $40,000 (N=6,803). This pattern is confounded by differences in house and medium. Sale-quarter midpoint errors range from 31.23% in 2024Q4 (N=353) to 47.51% in 2024Q1 (N=550); the largest recent cohorts are 33.93% in 2025Q4 (N=9,688), 36.08% in 2026Q1 (N=6,401), and 37.01% in 2026Q3 (N=2,413). These are sale-date groups, not model-run trends.

## Cars Results

The Cars comparison contains **151 lots from two events**, only about 10.69% of distinct URLs. There is no pooled Cars estimate-error result because the event samples and values differ substantially. Median inferred hammer is $150,000 for Gooding and $825,000 for RM Abu Dhabi.

| Event | Estimate | N | Median absolute % error | Median signed % error | Within +/-20% |
|---|---|---:|---:|---:|---:|
| Gooding Amelia Island 2025 | Low | 128 | 25.00% | +23.23% | 40.62% |
| Gooding Amelia Island 2025 | Midpoint | 128 | 37.38% | +37.38% | 25.00% |
| Gooding Amelia Island 2025 | High | 128 | 54.65% | +54.65% | 15.62% |
| RM Abu Dhabi 2025 | Low | 23 | 7.25% | 0.00% | 86.96% |
| RM Abu Dhabi 2025 | Midpoint | 23 | 11.11% | +9.76% | 86.96% |
| RM Abu Dhabi 2025 | High | 23 | 17.65% | +17.65% | 56.52% |

Gooding results are below / within / above the estimate range for **78.91% / 14.84% / 6.25%** of its sample. RM Abu Dhabi's corresponding shares are **47.83% / 43.48% / 8.70%**. Gooding's midpoint is above inferred hammer for much of its sample; the RM sample is closer to its estimates, but is too small to generalize to the wider Cars market. Four Gooding price-basis anomalies and the excluded Paris match need source-level review.

## Memorabilia Results

The final Memorabilia sample contains **2,360 lots**. Its midpoint median absolute percentage error is **36.84%**, median signed error is **+9.09%**, and median absolute USD error is **$528.75** among 2,300 lots with usable dollar values. Results are below / within / above the estimate range for **32.63% / 37.37% / 30.00%** of matched lots.

| Estimate point | Median absolute % error | Median signed % error | Within +/-10% | Within +/-20% | Within +/-30% |
|---|---:|---:|---:|---:|---:|
| Low | 33.33% | -14.19% | 17.75% | 31.74% | 46.82% |
| Midpoint | 36.84% | +9.09% | 14.19% | 27.97% | 42.42% |
| High | 46.34% | +33.33% | 12.29% | 24.07% | 33.60% |

| Auction house | N | Midpoint median absolute % error | Median signed % error | Within +/-20% | Within estimate range |
|---|---:|---:|---:|---:|---:|
| Freemans | 1,055 | 30.08% | +7.14% | 32.61% | 46.82% |
| Bonhams | 190 | 36.93% | +26.14% | 32.11% | 35.79% |
| Sotheby's | 787 | 44.44% | +21.43% | 22.11% | 29.61% |
| Christie's | 328 | 45.69% | -21.26% | 24.70% | 26.52% |

Freemans has the lowest observed house-level error, but 1,012 of its 1,055 lots are Sports, and its matched coverage is much higher than other houses. The difference is not a controlled comparison. By type, midpoint error is 31.71% for Sports (N=1,235), 35.58% for Automotive memorabilia (N=119), and 42.86% for Pop Culture (N=1,006). The automotive category here refers to memorabilia, not cars.

For 2,062 native-USD lots, midpoint error is 30.40% up to $400 (N=676), 29.98% from $400-$2,000 (N=382), 41.18% from $2,000-$8,000 (N=502), and 44.09% above $8,000 (N=502). Sale-quarter errors are 30.20% in 2025Q4 (N=388), 44.88% in 2026Q1 (N=305), 30.40% in 2026Q2 (N=1,018), and 43.33% in 2026Q3 (N=493). Changing house and lot mix likely explains some variation; these sale-date groups do not establish a time trend in estimate quality.

## Charts and Interpretation

### Cross-Asset Benchmark

![Midpoint error and within-20-percent accuracy by asset or event](daily_sales/memorabilia_report/05_cross_asset_benchmark.png)

**What it shows:** The left panel compares midpoint median absolute percentage error; the right panel shows the share of midpoints within 20% of the result.

**Result:** RM Abu Dhabi has the lowest midpoint error (11.11%) and highest within-20% share (86.96%), but represents only 23 cars. Artwork is at 34.98% / 29.98%, Gooding at 37.38% / 25.00%, and Memorabilia at 36.84% / 27.97%. These are separate populations and are not a controlled comparison across assets.

### Artwork

![Artwork hammer-price distribution](daily_sales/artwork_report/01_hammer_distribution.png)

**What it shows:** A frequency histogram of actual hammer prices for the 29,095-lot Artwork sample. The horizontal axis is log10 USD, making the wide spread of lot values visible without allowing the largest prices to dominate the scale.

**Result:** Artwork spans a broad price range. This is why the report uses percentage error for cross-value comparisons and separately reports dollar error; one metric alone cannot represent both typical proportional miss and financial magnitude.

![Artwork actual price versus estimate midpoint](daily_sales/artwork_report/02_actual_vs_midpoint.png)

**What it shows:** A 9,000-lot sample plotted on logarithmic axes, with actual hammer on the horizontal axis and estimate midpoint on the vertical axis. The diagonal is the equality line: points above it are midpoints above actuals, and points below it are midpoints below actuals.

**Result:** The full-sample midpoint median absolute percentage error is 34.98% and median signed error is +4.17%. The modest positive median bias coexists with substantial lot-level scatter, so the aggregate midpoint is not a close estimate for every lot.

![Artwork result position relative to estimate range](daily_sales/artwork_report/03_range_position.png)

**What it shows:** The share of actual hammers below the low estimate, within the inclusive published range, or above the high estimate.

**Result:** 31.52% fall below the range, 32.45% inside, and 36.03% above it. Roughly two thirds of recorded results are outside the published interval, split fairly evenly between its two sides.

![Artwork midpoint error by auction house](daily_sales/artwork_report/04_house_error.png)

**What it shows:** House-level median absolute percentage error for the estimate midpoint, ordered from lowest to highest observed error.

**Result:** Phillips is lowest at 32.35% (N=3,322); Hindman is highest at 44.67% (N=1,685). The differences are descriptive because value mix, medium mix, and eligibility coverage vary by house.

![Artwork error by estimated value band](daily_sales/artwork_report/05_estimated_value_error.png)

**What it shows:** Midpoint median absolute percentage error across four ascending quartiles of pre-sale estimated USD midpoint. The chart labels the quartiles Q1-Q4; these are value quartiles, not calendar quarters.

**Result:** Error falls from 44.21% in the lowest midpoint quartile (N=7,302) to 27.32% in the highest (N=6,803), with 38.89% and 32.51% in the middle quartiles. This association is descriptive and may reflect differences in house and medium composition.

![Artwork error by sale quarter](daily_sales/artwork_report/06_quarter_error.png)

**What it shows:** Midpoint median absolute percentage error over sale-date quarters. It is not based on the date a pricing model ran.

**Result:** Error varies by quarter, from 31.23% in 2024Q4 (N=353) to 47.51% in 2024Q1 (N=550). Large recent groups range from 33.93% in 2025Q4 to 37.01% in 2026Q3. Changing and sometimes small samples mean the plot does not establish improving or declining model performance over time.

### Cars

![Cars estimate error by event](daily_sales/cars_report/01_estimate_error_by_event.png)

**What it shows:** Low, midpoint, and high estimate median absolute percentage errors for Gooding Amelia Island 2025 and RM Abu Dhabi 2025, calculated against inferred hammers.

**Result:** Low estimates have the lowest error at both events. Gooding's errors rise from 25.00% (low) to 54.65% (high); RM's rise from 7.25% to 17.65%. Event, value, and sample composition differ, and RM has only 23 lots.

![Cars inferred hammer position relative to estimate range](daily_sales/cars_report/02_range_position_by_event.png)

**What it shows:** Stacked shares of inferred hammers below, within, and above each event's published estimate range.

**Result:** Gooding has 78.91% of results below range and only 14.84% within. RM Abu Dhabi has 47.83% below, 43.48% within, and 8.70% above. The contrast is event-specific and should not be generalized to all car sales.

### Memorabilia

![Memorabilia error by estimate point](daily_sales/memorabilia_report/01_estimate_error.png)

**What it shows:** Median absolute percentage error for the low, midpoint, and high estimate across 2,360 matched lots.

**Result:** Error increases from 33.33% for the low estimate to 36.84% for the midpoint and 46.34% for the high. The low estimate is closest by this metric, but its median signed error is -14.19%, so it tends to be below the recorded result.

![Memorabilia midpoint error by auction house](daily_sales/memorabilia_report/02_house_error.png)

**What it shows:** Midpoint median absolute percentage error by corrected auction-house label.

**Result:** Freemans is lowest at 30.08% (N=1,055); Christie's is highest at 45.69% (N=328). Freemans is heavily Sports/card-weighted and has 93.61% matched coverage, so the chart is not an adjusted house ranking.

![Memorabilia midpoint error by item type](daily_sales/memorabilia_report/03_type_error.png)

**What it shows:** Midpoint median absolute percentage error for Sports, Automotive memorabilia, and Pop Culture lots.

**Result:** Sports is lowest at 31.71% (N=1,235), followed by Automotive memorabilia at 35.58% (N=119), and Pop Culture at 42.86% (N=1,006). Type groups also differ in house, value, and item mix.

![Memorabilia midpoint error by sale quarter](daily_sales/memorabilia_report/04_quarter_error.png)

**What it shows:** Midpoint median absolute percentage error by sale quarter for matched lots with valid dates.

**Result:** Error ranges from 30.20% in 2025Q4 to 44.88% in 2026Q1, then 30.40% in 2026Q2 and 43.33% in 2026Q3. Quarter sample composition changes, and 156 matched lots have no valid sale date; this is not evidence of a model-run trend.

## Limitations and Next Analysis

- The exports do not contain item-level Barkr, Local Pricer, Standard, or Llama predictions. Their accuracy, paired win rates, coverage, and value beyond the auction midpoint cannot be calculated.
- Cars results cover just two events and 151 lots. The hammer prices are inferred by premium inversion and require source-level confirmation, including review of four Gooding anomalies and the excluded RM Paris match.
- Several price-basis and currency decisions are inferred. Confirm `ah_price`/`ah_bp_price` semantics and the 247 repaired Christie's currencies before external publication.
- House, type, value, and quarter comparisons are descriptive. Different coverage and population mix prevent causal or unadjusted ranking claims.
- Large percentage misses should be checked against original lot pages; very small recorded prices can dominate percentage-error rankings.
- Time groups use sale date. Pricing-run timestamps are missing, so model drift cannot be measured.

To complete the model comparison, provide a prediction row for each method and lot with a stable `lot_url`, method name, prediction value and currency, price basis, run timestamp, and prediction-availability flag. Compare methods only on the same eligible lots and use the latest valid prediction before each sale.

## Files and Reproducibility

- Detailed source report: [daily_sales/README.md](daily_sales/README.md)
- Artwork: [report tables and charts](daily_sales/artwork_report/), [analysis script](daily_sales/artwork_estimate_report.py)
- Cars: [report tables and charts](daily_sales/cars_report/), [analysis script](daily_sales/cars_estimate_report.py)
- Memorabilia: [report tables and charts](daily_sales/memorabilia_report/), [sample builder](daily_sales/memorabilia_estimate_sample.py), [summary script](daily_sales/memorabilia_estimate_report.py), [chart script](daily_sales/create_memorabilia_charts.py)
- The three current source JSON exports are tracked with [Git LFS](https://git-lfs.com/). The legacy `Data/OutputOld/` archive, `.venv/`, and Python cache files are excluded from Git.

## Conclusion

Auction-house estimates provide a useful but imperfect baseline: the low estimate has the smallest median absolute percentage error in every analyzed sample, while midpoint errors remain about 35%-37% for Artwork, Gooding Cars, and Memorabilia. RM Abu Dhabi's lower error is promising only for that small 23-car event sample. Data coverage, currency and premium treatment, and differences in lot mix materially affect the results. Most importantly, the available exports do not include Barkr or local-pricer predictions, so no conclusion about those models is supported yet. A fair model comparison requires item-level predictions matched to the same lots, verified price basis, and run timestamps.