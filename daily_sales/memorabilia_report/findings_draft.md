# Memorabilia daily pricing analysis — draft findings

Data extracted 25 September 2026. This report compares auction-house estimates with recorded auction results. The export has no Barkr, Local Pricer, Standard, or Llama predictions, so those requested comparisons remain open.

## Sample and method

- The export contains 4,812 rows and 4,782 distinct lot URLs. Thirty URLs repeat, with no conflicting recorded prices, estimates, or currencies among their rows. We combine matching fields by URL.
- We include every exported row in the source population, including trading cards and baseball cards. The analysis sample contains 2,360 unique lots with a positive `ah_price`, positive ordered low/high estimates, and a usable currency.
- We compare estimates with `ah_price` in each lot's native currency. The ratio of `ah_bp_price` to `ah_price` is usually 1.20–1.28, supporting `ah_price` as the pre-premium price proxy and `ah_bp_price` as the premium-inclusive result. This convention should be confirmed with the data owner before publication.
- We infer currency for 247 matched Christie's lots with missing currency: 221 Jim Irsay lots are USD and 26 Groundbreakers lots are GBP, based on their Christie's sale pages. All such rows are flagged in `memorabilia_estimate_sample.csv`.
- The 715 rows labelled `Unknown Marketplace` have Freemans lot URLs and are grouped under Freemans. One row labelled Goldin has a Sotheby's URL, but it does not enter the matched estimate sample.
- There is no sale-status field. A positive recorded price is used as evidence of a priced result. A missing price is not treated as zero or as proof that a lot was unsold.

## Main results

| Auction-house estimate | N | Median absolute percentage error | Median signed percentage error | Within ±10% | Within ±20% | Within ±30% |
|---|---:|---:|---:|---:|---:|---:|
| Low | 2,360 | 33.33% | −14.19% | 17.75% | 31.74% | 46.82% |
| Midpoint | 2,360 | 36.84% | +9.09% | 14.19% | 27.97% | 42.42% |
| High | 2,360 | 46.34% | +33.33% | 12.29% | 24.07% | 33.60% |

Recorded results fall below the estimate range for 32.63% of matched lots, within it for 37.37%, and above it for 30.00%. The low estimate has a smaller median percentage error than the midpoint on this sample.

The midpoint's median absolute dollar error is **$528.75** and median signed dollar error is **+$45.00**, calculated for 2,300 lots with usable USD values. Native USD amounts are used for USD lots; the export's USD fields are used for 238 GBP lots. The actual and estimate conversion rates agree within 1% for all 238 of those GBP lots. Sixty GBP lots lack complete USD values and are excluded only from dollar-error metrics.

## Segment results

- **Auction house:** Median midpoint error is 30.08% at Freemans (N=1,055), 36.93% at Bonhams (N=190), 44.44% at Sotheby's (N=787), and 45.69% at Christie's (N=328). This is a description of the available matched lots, not a controlled house ranking.
- **Selection:** The analysis sample covers 93.61% of Freemans' distinct exported lots, 43.33% of Christie's, 34.90% of Sotheby's, and 29.55% of Bonhams'. This unequal availability can affect house comparisons.
- **Type:** Median midpoint error is 31.71% for Sports (N=1,235), 35.58% for Automotive (N=119), and 42.86% for Pop Culture (N=1,006). Freemans contributes 1,012 of the Sports lots, while Sotheby's contributes 565 of the Pop Culture lots. Thus the overall house differences partly reflect item mix.
- **Within Sports:** Freemans' median error is 29.96% across 1,012 lots; Sotheby's is 56.25% across 195 lots. Freemans has 639 Baseball lots and 206 Basketball lots; Sotheby's has 140 Basketball lots but only 8 Baseball lots. Among Basketball lots, median errors are 31.15% at Freemans (N=206) and 61.82% at Sotheby's (N=140), though their pre-sale estimated values also differ markedly.
- **Pre-sale value:** Among 2,062 USD-denominated matched lots, midpoint median error is about 30% for the two lowest midpoint-value quartiles, 41.18% for the third, and 44.09% for the highest. These are bands of the published midpoint, rather than bands of realized prices. The higher bands contain a different house and item mix; do not infer that higher value itself causes worse accuracy.
- **Sale quarter:** Median midpoint error is 30.20% in 2025Q4 (N=388), 44.88% in 2026Q1 (N=305), 30.40% in 2026Q2 (N=1,018), and 43.33% in 2026Q3 (N=493). Another 156 matched lots have no valid sale date. There is no pricing-run date in this export; quarter is based on sale date only. The changing house and sale mix limits trend interpretation.

## Largest misses and data quality

- The largest percentage overestimate is a Sotheby's Grateful Dead lot recorded at 300 against a midpoint of 6,000 (1,900% error). Other large overestimates include several tennis and game-worn sports lots.
- The largest percentage underestimates include Christie's music and pop-culture items, for example a Bob Dylan Newport Folk Festival program recorded at 10,054.17 against a midpoint of 400. Because percentage underestimation is bounded at 100% for positive estimates, rank overestimates and underestimates separately.
- The largest dollar misses are high-value Christie's guitars, a literary manuscript, and a Sotheby's Aaron Judge jersey. A large dollar miss and a large percentage miss identify different kinds of lots.
- Thirty duplicated URLs, the house-label errors, missing currencies, and 156 missing sample sale dates are recorded in the sample and tables. Extreme misses should be checked against source lot pages before assigning causes such as condition, rarity, or provenance.

## Remaining work

1. Obtain Barkr, Local Pricer, Standard, and Llama predictions at lot level, including lot URL or another join key, prediction timestamp, currency, and hammer/premium price basis. Then compare all methods on the same matched lots and measure value beyond the auction-house midpoint.
2. Confirm the `ah_price` basis and inferred Christie's currencies with the data owner before external publication.
3. Review the largest outlier lot pages and, if useful, add narrower item attributes such as card versus game-worn memorabilia and condition. These causes cannot be established from the available fields alone.

The companion CSV tables and outlier lists in this folder are rebuilt by `memorabilia_estimate_report.py` from `memorabilia_estimate_sample.csv`, which is rebuilt by `memorabilia_estimate_sample.py` from the raw export.
