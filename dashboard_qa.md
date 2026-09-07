# Sprint 4 Dashboard QA

Date: 7 September 2026

## Automated Tests

- Full pytest suite: 200 passed
- Test failures: 0

## Dashboard Screens

1. Home — verified
2. Company Profile — verified
3. Screener — verified
4. Peer Comparison — verified
5. Trend Analysis — verified
6. Sector Analysis — verified
7. Capital Allocation — verified
8. Annual Reports — verified

## Representative Ticker QA

Verified dashboard data access for:

- INDIGO
- TCS
- HDFCBANK
- ITC
- ONGC
- SUNPHARMA
- RELIANCE
- BHARTIARTL
- COALINDIA
- ASIANPAINT

All returned valid data through the shared dashboard loaders.

## Partial History

- ADANIGREEN — 8 years
- ATGL — 7 years
- JIOFIN — 2 years
- LICI — 6 years

The dashboard handles shorter histories without requiring ten years of data.

## Screener Edge Case

Extreme filter values were applied.

Result:

0 companies match your filters

No crash or error occurred.

## Annual Report Edge Case

Missing annual-report URLs display:

- No report URL available.
- Report unavailable

Valid BSE URLs remain clickable.

## Valuation Outputs

valuation_summary.xlsx:

- 92 rows
- 10 required columns
- Fair: 48
- Discount: 30
- Caution: 14

valuation_flags.csv:

- 44 rows
- Discount: 30
- Caution: 14

## Data Notes

- 92 companies are available to the dashboard.
- The current sector mapping contains 10 populated broad sectors.
- Some companies have fewer than ten years of historical data.
- Some companies have missing pros/cons records.
