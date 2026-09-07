# Nifty 100 Financial Intelligence Platform

## Sprint 4 Dashboard

### Run Dashboard

From the project root:

python -m streamlit run src/dashboard/app.py

Dashboard URL:

http://localhost:8501

### Dashboard Screens

1. Home — Portfolio KPIs, sector breakdown, and top composite-score companies.
2. Company Profile — Company search, financial KPIs, historical charts, and pros/cons.
3. Screener — Financial filters, presets, live results, and CSV export.
4. Peer Comparison — Peer-group selection, benchmark comparison, radar chart, and comparison table.
5. Trend Analysis — Multi-metric historical trend analysis.
6. Sector Analysis — Revenue/ROE bubble analysis and sector median KPIs.
7. Capital Allocation — Cash-flow pattern treemap and company drill-down.
8. Annual Reports — Searchable annual-report years and BSE report links.

### Valuation Outputs

The valuation module generates:

- output/valuation_summary.xlsx
- output/valuation_flags.csv

valuation_summary.xlsx contains 92 companies with:

- P/E
- P/B
- EV/EBITDA
- FCF yield
- 5-year median P/E
- P/E versus sector median
- valuation flag

valuation_flags.csv contains only Caution and Discount companies.

### Testing

Full automated regression test suite:

200 passed

### Sprint 4 QA

QA documentation:

- dashboard_qa.md
- sprint4_retro.md

### Data Notes

- Dashboard coverage: 92 companies.
- Market-cap history: 2019–2024.
- Some companies have fewer than 10 years of historical data.
- Missing annual-report URLs are shown as unavailable.
- Missing pros/cons data is handled without crashing.