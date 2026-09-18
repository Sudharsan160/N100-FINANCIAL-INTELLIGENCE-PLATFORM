import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/valuation")
def valuation_summary():
    """
    Return latest valuation metrics and simple valuation flags
    calculated from market-cap and cash-flow data.
    """

    conn = get_connection()

    try:
        companies = conn.execute("""
            SELECT id, company_name
            FROM companies
            ORDER BY id
            """).fetchall()

        results = []

        for company in companies:
            ticker = company["id"]

            market = conn.execute(
                """
                SELECT *
                FROM market_cap
                WHERE company_id = ?
                ORDER BY year DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()

            ratios = conn.execute(
                """
                SELECT *
                FROM financial_ratios
                WHERE company_id = ?
                ORDER BY year DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()

            if not market:
                continue

            market_cap = market["market_cap_crore"]
            fcf = ratios["free_cash_flow_cr"] if ratios else None

            fcf_yield = None

            if market_cap is not None and market_cap > 0 and fcf is not None:
                fcf_yield = (fcf / market_cap) * 100

            pe = market["pe_ratio"]

            if pe is None:
                valuation_flag = "Unavailable"
            elif pe >= 50:
                valuation_flag = "High P/E"
            elif pe >= 30:
                valuation_flag = "Elevated P/E"
            elif pe <= 15:
                valuation_flag = "Low P/E"
            else:
                valuation_flag = "Moderate P/E"

            results.append(
                {
                    "ticker": ticker,
                    "company_name": company["company_name"],
                    "year": market["year"],
                    "market_cap_crore": market_cap,
                    "pe_ratio": pe,
                    "pb_ratio": market["pb_ratio"],
                    "ev_ebitda": market["ev_ebitda"],
                    "dividend_yield_pct": (market["dividend_yield_pct"]),
                    "free_cash_flow_cr": fcf,
                    "fcf_yield_pct": fcf_yield,
                    "valuation_flag": valuation_flag,
                }
            )

        return {
            "count": len(results),
            "data": results,
        }

    finally:
        conn.close()


@router.get("/market-cap/{ticker}")
def market_cap_history(ticker: str):
    """Return market-cap and valuation history for a company."""

    conn = get_connection()

    try:
        company = conn.execute(
            """
            SELECT id, company_name
            FROM companies
            WHERE UPPER(id) = UPPER(?)
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()

        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found.",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM market_cap
            WHERE company_id = ?
            ORDER BY year
            """,
            (company["id"],),
        ).fetchall()

        return {
            "ticker": company["id"],
            "company_name": company["company_name"],
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()
