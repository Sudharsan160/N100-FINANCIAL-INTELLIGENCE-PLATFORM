import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.dashboard.utils.db import get_companies, get_ratios

client = TestClient(app)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"


def get_broad_sector(company_id: str):
    """Return the company's broad sector from the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            """
            SELECT broad_sector
            FROM sectors
            WHERE company_id = ?
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

        return row["broad_sector"] if row else None
    finally:
        conn.close()


def test_dashboard_screener_data_matches_api():
    """
    Verify that the dashboard's SQLite-backed screener data path
    produces the same company set as the FastAPI screener for
    equivalent filters.
    """

    min_roe = 10.0
    max_de = 2.0

    # API result.
    api_response = client.get(
        "/api/v1/screener",
        params={
            "min_roe": min_roe,
            "max_de": max_de,
        },
    )

    assert api_response.status_code == 200

    api_data = api_response.json()

    api_tickers = {company["ticker"] for company in api_data["data"]}

    # Dashboard data path.
    companies = get_companies()

    dashboard_tickers = set()

    for ticker in companies["company_id"].dropna().astype(str):
        ratios = get_ratios(ticker)

        if ratios.empty:
            continue

        ratios["year"] = ratios["year"].astype(float)

        latest = ratios.sort_values("year").iloc[-1]

        roe = latest.get("return_on_equity_pct")
        debt_to_equity = latest.get("debt_to_equity")

        if roe is None or debt_to_equity is None:
            continue

        broad_sector = get_broad_sector(ticker)

        is_financials = (
            broad_sector is not None and broad_sector.strip().casefold() == "financials"
        )

        if float(roe) >= min_roe and (is_financials or float(debt_to_equity) <= max_de):
            dashboard_tickers.add(ticker)

    assert dashboard_tickers == api_tickers
    assert len(dashboard_tickers) == api_data["count"]
