# Artwork daily pricing analysis — draft findings

Data extracted 25 September 2026. Scope: Artwork daily-sale records and auction-house estimates. Barkr, Local Pricer, Standard, and Llama predictions are absent from this export, so their accuracy and value beyond the auction estimate cannot yet be measured.

## Sample and method

- The extraction returned 43,530 rows from six auction houses, with no retrieval failures. The earlier extraction had 41,931 rows; the increase does not establish how many distinct lots are new.
- Estimate strings with comma separators were parsed as numbers. We excluded 134 lot URLs with conflicting house, hammer, or estimate values. We then retained one most-complete record per remaining URL, leaving 39,976 unique lots.
- The analysis uses 29,095 lots with a positive `ah_price` and a valid positive low–high estimate range. Comparison uses each lot's native currency. Dollar errors use the provided USD fields.
- `ah_price` is treated as hammer price and `ah_bp_price` as premium-inclusive result: their ratio is typically about 1.20. The published estimate is treated as hammer-basis. Confirm this convention with the data owner before external publication.
- Of the 39,976 retained lots, 7,738 have an explicit `sold` status and 1,896 an explicit `unsold` status, all from Sotheby's. The other houses have no status value: 23,389 of those records have a positive hammer price and 6,953 do not. Missing price is not zero and missing status is not labelled unsold.

## Main results

| Auction-house estimate | N | Median absolute percentage error | Median signed percentage error | Median absolute USD error | Within ±10% | Within ±20% | Within ±30% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Low | 29,095 | 33.55% | −16.29% | $3,105.81 | 19.10% | 34.22% | 45.99% |
| Midpoint | 29,095 | 34.98% | +4.17% | $3,525.00 | 13.45% | 29.98% | 42.79% |
| High | 29,095 | 41.73% | +25.00% | $4,275.60 | 11.10% | 23.43% | 35.15% |

Hammer prices fell below the published range in 31.52% of lots, within it in 32.45%, and above it in 36.03%. The low estimate has a slightly lower median absolute percentage error than the midpoint on this sample. This does not make the low estimate a universal replacement for the midpoint; performance varies by segment and error measure.

## Segments

- **Auction house:** Midpoint median absolute percentage error ranges from 32.35% at Phillips (N=3,322) to 44.67% at Hindman (N=1,685). House samples differ substantially in median sold value and usable-price coverage, so this is descriptive rather than a controlled ranking.
- **Pre-sale estimated value:** Midpoint error is 44.21% in the lowest estimated-value quartile (up to $3,500), 38.89% in the next ($3,500–$10,000), 32.51% in the next ($10,000–$40,000), and 27.32% in the highest (above $40,000). The lowest quartile falls below its estimate range most often (36.96%). These bands use estimates rather than realized prices to avoid sorting lots by the outcome being evaluated.
- **Medium:** Paintings (N=10,292) and prints (N=5,078) have median errors of 33.55% and 33.04%. Furniture is 49.80% (N=745); photographs, ceramics, and decorative arts are around 40–41%. Medium groups also differ in value and auction-house mix.
- **Sale quarter:** Recent large-sample quarters are approximately 34–37% median error. Earlier quarters have much smaller counts. Ninety-two analysis lots lack a valid sale date. The file has no pricing-run date, so this is a sale-date view only.

## Data quality and outliers

- There are 1,868 repeated lot URLs in the raw export. Of those, 117 have conflicting hammer prices; 123 appear under more than one auction-house label. IDs are not a reliable deduplication key because some repeat across different lots.
- All 20 largest percentage misses are results below their estimate ranges. One suspicious retained lot has a recorded hammer of GBP 0.83 ($1.05) against an estimate of GBP 400–600. It should be checked against the source listing before interpreting its extreme percentage error.
- The 20 largest absolute dollar misses are dominated by high-value works (17 paintings). Ten results are above the midpoint and ten below. A large dollar error at this end does not itself indicate bad data.
- For 124 analysis lots, the USD conversion implied by the estimates differs by more than 1% from the conversion implied by the hammer price. Excluding those rows leaves both the midpoint median absolute USD error ($3,525) and median absolute percentage error (34.98%) unchanged at the reported precision.

## Next actions

1. Confirm the estimate and hammer price-basis conventions with the data owner, and review the suspicious low-price source listing.
2. Obtain item-level Barkr, Local Pricer, Standard, and Llama predictions with run dates, currencies, price bases, and a matching key such as lot URL. Compare methods only on matched lots.
3. Share the summary table, five to six charts, and the stated sample rules. Do not present unavailable prediction comparisons as completed.

## Files

The `artwork_estimate_report.py` script in `daily_sales` rebuilds the sample, tables, and six PNG charts in this folder from `artwork_daily_sale.json`.
