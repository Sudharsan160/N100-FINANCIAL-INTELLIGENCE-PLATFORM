import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException

router = APIRouter()

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_url_valid(url):
    """Check whether a document URL has a valid HTTP/HTTPS structure."""
    if not url:
        return False

    try:
        parsed = urlparse(url)

        if parsed.scheme not in {
            "http",
            "https",
        }:
            return False

        return bool(parsed.netloc)

    except ValueError:
        return False


@router.get("/companies/{ticker}/documents")
def company_documents(ticker: str):
    """Return annual reports and URL validity for a company."""

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
            SELECT
                id,
                company_id,
                year,
                annual_report
            FROM documents
            WHERE company_id = ?
            ORDER BY year DESC
            """,
            (company["id"],),
        ).fetchall()

        documents = []

        for row in rows:
            item = dict(row)

            item["is_url_valid"] = is_url_valid(item["annual_report"])

            documents.append(item)

        return {
            "ticker": company["id"],
            "company_name": company["company_name"],
            "count": len(documents),
            "documents": documents,
        }

    finally:
        conn.close()
