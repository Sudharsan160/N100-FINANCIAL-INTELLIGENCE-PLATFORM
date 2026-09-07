# Sprint 4 Retrospective

## Completed

Sprint 4 delivered the Streamlit dashboard and valuation module.

The dashboard contains eight screens:

- Home
- Company Profile
- Screener
- Peer Comparison
- Trend Analysis
- Sector Analysis
- Capital Allocation
- Annual Reports

The valuation module generates:

- output/valuation_summary.xlsx
- output/valuation_flags.csv

## UX Decisions

- Wide Streamlit layout for analytical tables and charts.
- Sidebar navigation and filtering.
- Company search by ticker or company name.
- Missing data handled without crashing.
- Annual report links shown only when usable.
- Screener results exportable to CSV.

## Data Edge Cases

Partial-history companies:

- ADANIGREEN
- ATGL
- JIOFIN
- LICI

The dashboard displays available history for these companies.

Some companies do not have pros/cons records; the Profile screen displays an availability message.

## Performance and Testing

Full automated regression suite:

200 passed

Representative company data-loader checks completed successfully.

Extreme screener testing returned 0 matching companies without a crash.

## Valuation

The valuation summary contains all 92 companies.

Flags:

- Fair: 48
- Discount: 30
- Caution: 14

The flagged CSV contains 44 companies.

## Sprint Outcome

Sprint 4 implementation and completed QA checks are documented and ready for final review.
