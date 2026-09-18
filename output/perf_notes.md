\# Sprint 6 Day 43 — Performance \& Integration Notes



\## API Load Test

\- Endpoint: GET /api/v1/screener

\- Concurrent requests: 10

\- Total client time: 0.436 seconds

\- HTTP 200 responses: 10/10

\- Target: < 10 seconds

\- Result: PASS



\## Dashboard Company Profile Performance

\- TCS: < 1 second

\- INFY: < 1 second

\- RELIANCE: < 1 second

\- HDFCBANK: < 1 second

\- ITC: < 1 second

\- Target: < 3 seconds per ticker

\- Result: PASS



\## End-to-End Integration

\- FastAPI: port 8000

\- Streamlit: port 8501

\- Port conflict: None

\- Dashboard loaded successfully: PASS

\- API data available to dashboard: PASS

\- Streamlit screener/API comparison: PENDING



\## Bottlenecks

\- No significant performance bottleneck identified.

\- Streamlit displayed deprecation warnings for `use\_container\_width`; cleanup planned for Day 44.

