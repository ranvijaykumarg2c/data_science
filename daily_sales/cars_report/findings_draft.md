# Cars daily pricing analysis — draft findings

Data extracted 25 September 2026. This analysis covers auction-house estimates only. The export has no Barkr, Local Pricer, Standard, or Llama predictions.

## Sample and method

- The Cars export has 1,666 rows and 1,412 distinct lot URLs. There are 254 repeated-URL rows, seven URLs with conflicting sold prices, 487 rows without an auction-house label, and 386 rows without a sale date.
- Some RM Sotheby's pre-sale estimates and sold results occupy separate rows. Matching on `lot_url` yields 156 lots with a positive result and valid estimate range: 132 Gooding Amelia Island 2025, 23 RM Abu Dhabi 2025, and one RM Paris 2026.
- The Paris lot is excluded because the two rows have different sale dates and its EUR premium basis was not established. Four Gooding lots are also excluded from the headline comparison because their published sold amounts do not yield a plausible round bid under the published premium schedule. The final comparison has **151 lots across two auction events**. None of these matched URLs has conflicting sold prices.
- The `current_status` field describes vehicle registration or condition. It is not a sold/unsold outcome field. A positive published result is used as evidence of a sale for the analyzed lots; missing price is not treated as zero or as unsold.
- In all 993 rows with both fields populated, `ah_price` equals `ah_bp_price`; these fields do not independently distinguish hammer from premium-inclusive price in this Cars export.

### Price basis

For Gooding, the exported result matches the [official lot page's sold amount](https://www.goodingco.com/lot/1997-porsche-993-turbo-1/). The [2025 auction page](https://www.goodingco.com/auction/amelia-island-auction-2025/false/auction/amelia-island-auction-2025) links to [conditions](https://www.goodingco.com/terms/) stating that estimates exclude buyer's premium and vehicle premiums are 12% through $250,000 hammer and 10% above. We inverted that schedule to infer a hammer price. The resulting hammer is within $1 of a $100 bid increment for 128 of 132 matched Gooding lots. The [Ford GT40 miniature](https://www.goodingco.com/lot/1968-automobile-scaf-ford-gt40/), [Lamborghini Miura](https://www.goodingco.com/lot/1968-lamborghini-miura-p400-s-1a/), [Peugeot](https://www.goodingco.com/lot/1938-peugeot-402-darlmat-special-sport-coupe/), and [BMW Z8](https://www.goodingco.com/lot/2001-bmw-z8-1b/) pages confirm their exported sold amounts; their premium basis remains uncertain. They are excluded from the headline and retained in `gooding_basis_anomalies.csv`. Including them leaves the midpoint median percentage error at 37.38%.

For RM Abu Dhabi, the [event's bidder information](https://rmsothebys.com/auctions/ad25/bidder-info/) states 15% premium through $200,000 hammer and 12.5% above. We inverted that schedule for the 23 USD matched lots. All 23 implied hammer prices are within $1 of a $100 bid increment. The [Pagani lot page](https://rmsothebys.com/auctions/ad25/lots/r0002-2006-pagani-zonda-riviera/) shows the published sold amount used in the export. These are **inferred** hammers, not a field supplied by the dataset.

## Results

| Event | Estimate | N | Median inferred hammer | Median absolute percentage error | Median signed percentage error | Median absolute dollar error | Within ±20% |
|---|---|---:|---:|---:|---:|---:|---:|
| Gooding Amelia Island 2025 | Low | 128 | $150,000 | 25.00% | +23.23% | $41,250 | 40.62% |
| Gooding Amelia Island 2025 | Midpoint | 128 | $150,000 | 37.38% | +37.38% | $67,500 | 25.00% |
| Gooding Amelia Island 2025 | High | 128 | $150,000 | 54.65% | +54.65% | $90,000 | 15.62% |
| RM Abu Dhabi 2025 | Low | 23 | $825,000 | 7.25% | 0.00% | $50,000 | 86.96% |
| RM Abu Dhabi 2025 | Midpoint | 23 | $825,000 | 11.11% | +9.76% | $150,000 | 86.96% |
| RM Abu Dhabi 2025 | High | 23 | $825,000 | 17.65% | +17.65% | $250,000 | 56.52% |

For the midpoint, Gooding has 10.94%, 25.00%, and 39.84% of lots within ±10%, ±20%, and ±30% of inferred hammer. RM Abu Dhabi has 43.48%, 86.96%, and 95.65%. Gooding results fall below, within, and above the estimate range 78.91%, 14.84%, and 6.25% of the time; RM Abu Dhabi results do so 47.83%, 43.48%, and 8.70% of the time.

The low estimate has the smallest median error for **both** events. Gooding and Abu Dhabi differ strongly in value and lot mix: their median inferred hammers are $150,000 and $825,000. The sample sizes also differ, so their numbers are descriptive event-level results rather than a general ranking of auction houses.

## Outliers and limits

- All 20 largest percentage misses are Gooding lots that sold below the low estimate. The four excluded Gooding prices warrant a premium-basis review; the source pages confirm that the exported sold amounts themselves are accurate.
- Fourteen of the 20 largest absolute dollar misses are Gooding lots and six are RM Abu Dhabi lots. Dollar error depends heavily on vehicle value; compare percentage and dollar errors together.
- Gooding's 133 source rows have no `sale_date`; RM estimate and result rows can carry different dates. Use the event dates from the source sites for event summaries, not row-level dates for a time trend.
- The two events are a small and selected subset of the 1,412 distinct lot URLs. Results should not be presented as accuracy for all Cars lots or all auction houses.

## Next actions

1. Review the four Gooding price-basis anomalies and the Paris EUR match against their original sale terms.
2. Obtain item-level Barkr, Local Pricer, Standard, and Llama predictions, including currency, price basis, run date, and a lot key, before attempting model comparisons.
3. Share the two-event summary table and charts with the sample and inferred-price-basis notes intact.

The `cars_estimate_report.py` script in `daily_sales` rebuilds all tables, review files, and two charts in this folder.
