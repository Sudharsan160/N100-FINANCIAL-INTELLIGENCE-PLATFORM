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
