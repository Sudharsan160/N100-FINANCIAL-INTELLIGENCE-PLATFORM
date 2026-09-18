# Nifty 100 Financial Intelligence Platform

Financial intelligence platform for 92 companies in the supplied Nifty 100 dataset. The project combines Excel ETL, SQLite analytics, a Streamlit dashboard, FastAPI services, financial screening, peer analysis, cash-flow intelligence, KMeans clustering, and generated PDF reports.

## Current platform

- 92 companies in the current database.
- 10 broad sectors in the supplied sector data.
- 8 Streamlit dashboard screens.
- FastAPI REST API under `/api/v1`.
- Five KMeans company archetypes.
- 92 company tearsheets.
- 10 sector reports.
- Portfolio summary PDF with one company per page.
- Automated unit, integration, and performance tests.

## Project structure

```text
src/
  api/
    main.py
    routers/
  analytics/
  dashboard/
    app.py
    pages/
    utils/
  etl/
  reports/

data/
  raw/

output/
reports/
tests/
  api/
  etl/
  kpi/
  performance/
  ratios/
  screener/
```

## Run the dashboard

From the project root with the virtual environment activated:

```powershell
python -m streamlit run src\dashboard\app.py
```

Dashboard:

```text
http://localhost:8501
```

### Dashboard screens

1. Home - Portfolio KPIs, sector breakdown, and composite-score overview.
2. Company Profile - Company search, financial KPIs, historical charts, and pros/cons.
3. Screener - Financial, growth, valuation, leverage, and dividend filters with CSV export.
4. Peer Comparison - Peer-group metrics, benchmark comparison, and radar visualization.
5. Trend Analysis - Historical metric trends.
6. Sector Analysis - Sector medians, growth, ROE, and distribution views.
7. Capital Allocation - Cash-flow sign patterns and capital-allocation classification.
8. Annual Reports - Annual-report years and external report links.

## Run the API

Start FastAPI from the project root:

```powershell
python -m uvicorn src.api.main:app --port 8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

Health endpoint:

```text
http://127.0.0.1:8000/api/v1/health
```

### API endpoint groups

- Companies: list, profile, P&L, balance sheet, cash flow, ratios, tearsheet.
- Screener: filtered company results.
- Sectors: sector list and sector company list.
- Peers: peer group membership and peer comparison.
- Valuation: valuation summary and market-cap history.
- Portfolio: latest KPI statistics.
- Documents: annual reports and URL-format status.
- Health: API and database health information.

## Core analytics

### Financial KPIs

The platform calculates or exposes metrics including:

- Net profit margin
- Operating profit margin
- ROE and ROA
- Debt to equity
- Asset turnover
- Revenue CAGR and PAT CAGR
- Free cash flow margin
- CFO to PAT
- CFO to total debt
- CapEx intensity
- FCF conversion
- Investing cash flow to CFO
- Financing cash flow to CFO

### Cash Flow Intelligence

Generated output:

```text
output/cashflow_intelligence.xlsx
output/distress_alerts.csv
```

The module classifies CFO quality, CapEx intensity, distress signals, deleveraging, and eight cash-flow sign patterns.

### Clustering

KMeans configuration:

- 5 clusters
- random_state=42
- StandardScaler
- Median imputation before scaling

Features:

- Return on equity percentage
- Debt to equity
- Revenue CAGR 5Y
- FCF CAGR 5Y
- Operating profit margin percentage

Outputs:

```text
output/cluster_labels.csv
output/cluster_profile.csv
output/outlier_report.csv
output/portfolio_stats.csv
reports/elbow_plot.png
reports/correlation_heatmap.png
```

Current cluster labels are:

- Turnaround / Cyclical
- Defensive Quality
- Value / Balanced
- High-Quality Compounders
- Emerging Growth

## Reports

### Company reports

```text
reports/tearsheets/
```

Current Sprint 5 output contains 92 company tearsheets.

### Sector reports

```text
reports/sector/
```

The supplied sector mapping currently contains 10 broad sectors, so the project generates 10 sector reports rather than inventing an eleventh sector.

### Portfolio report

```text
reports/portfolio/portfolio_summary.pdf
```

The current portfolio summary contains one company per page.

### Radar charts

```text
reports/radar_charts/
```

Company-level peer comparison radar images.

## Valuation outputs

```text
output/valuation_summary.xlsx
output/valuation_flags.csv
```

The valuation workflow includes P/E, P/B, EV/EBITDA, dividend yield, FCF yield, and valuation flags.

## Testing

Run the complete test suite with:

```powershell
python -m pytest -q
```

Generate an HTML test report with:

```powershell
python -m pytest -q --html=reports\day42_test_report.html --self-contained-html
```

Day 42 was verified with 221 passing tests and 0 failures. Day 43 adds API performance and dashboard/API integration tests; rerun the full suite after those additions to refresh the exact baseline.

## Data quality

The validator implements DQ-01 through DQ-16, including:

- Primary-key uniqueness
- Company/year uniqueness
- Foreign-key integrity
- Balance-sheet consistency
- Operating margin cross-check
- Positive sales
- Net-cash consistency
- Tax-rate sanity
- Dividend cap
- URL-format validation
- EPS sign consistency
- BSE balance checks
- Year coverage
- Company coverage
- Duplicate-row detection
- Required-field completeness

Validation output:

```text
output/validation_failures.csv
```

## Known data notes

- The current database contains 92 companies.
- The supplied broad-sector mapping contains 10 sectors.
- Some historical tables contain duplicate company/year records; these are documented and tested rather than silently removed.
- Some companies have fewer than 10 years of history.
- Some older annual-report records have missing URLs.
- Some clustering statistics contain extreme values because of the supplied source data.
- The documents API checks URL structure; it does not prove remote URL reachability.

## Documentation

- `dashboard_qa.md` - Dashboard QA notes.
- `sprint4_retro.md` - Sprint 4 retrospective.
- `sprint5_qa.md` - Sprint 5 QA notes and known data/spec mismatch.
- `docs/analyst_guide.pdf` - Analyst operating and interpretation guide.

## Operational smoke test

1. Activate the virtual environment.
2. Start FastAPI on port 8000.
3. Start Streamlit on port 8501 in a second terminal.
4. Check `/api/v1/health` returns HTTP 200.
5. Open the dashboard and test the Screener.
6. Open a company profile and annual-report view.
7. Run the full pytest suite before release.

## Important interpretation note

The platform provides historical data, calculations, screening, peer comparison, clustering, and reporting. Outputs should be interpreted in the context of sector, accounting structure, data quality, and the available historical period. The platform is an analytical tool rather than a standalone decision engine.
