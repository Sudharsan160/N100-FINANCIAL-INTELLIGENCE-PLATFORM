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


@router.get("/sectors")
def list_sectors():
    """Return all sectors with company counts and latest KPI medians."""

    conn = get_connection()

    try:
        sectors = conn.execute("""
            SELECT DISTINCT broad_sector
            FROM sectors
            WHERE broad_sector IS NOT NULL
            ORDER BY broad_sector
            """).fetchall()

        results = []

        for sector_row in sectors:
            sector_name = sector_row["broad_sector"]

            companies = conn.execute(
                """
                SELECT company_id
                FROM sectors
                WHERE broad_sector = ?
                """,
                (sector_name,),
            ).fetchall()

            company_ids = [row["company_id"] for row in companies]

            if not company_ids:
                continue

            placeholders = ",".join("?" for _ in company_ids)

            ratios = conn.execute(
                f"""
                SELECT *
                FROM financial_ratios
                WHERE company_id IN ({placeholders})
                  AND year = (
                      SELECT MAX(fr2.year)
                      FROM financial_ratios fr2
                      WHERE fr2.company_id =
                            financial_ratios.company_id
                  )
                """,
                company_ids,
            ).fetchall()

            roes = [
                row["return_on_equity_pct"]
                for row in ratios
                if row["return_on_equity_pct"] is not None
            ]

            opms = [
                row["operating_profit_margin_pct"]
                for row in ratios
                if row["operating_profit_margin_pct"] is not None
            ]

            des = [
                row["debt_to_equity"]
                for row in ratios
                if row["debt_to_equity"] is not None
            ]

            def median(values):
                if not values:
                    return None

                values = sorted(values)
                n = len(values)
                mid = n // 2

                if n % 2:
                    return values[mid]

                return (values[mid - 1] + values[mid]) / 2

            results.append(
                {
                    "sector": sector_name,
                    "company_count": len(company_ids),
                    "median_roe": median(roes),
                    "median_opm": median(opms),
                    "median_debt_to_equity": median(des),
                }
            )

        return {
            "count": len(results),
            "sectors": results,
        }

    finally:
        conn.close()


@router.get("/sectors/{sector}/companies")
def sector_companies(sector: str):
    """Return companies belonging to a broad sector."""

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                s.company_id AS ticker,
                c.company_name,
                s.broad_sector,
                s.sub_sector,
                s.market_cap_category,
                c.roe_percentage,
                c.roce_percentage
            FROM sectors s
            JOIN companies c
                ON c.id = s.company_id
            WHERE LOWER(s.broad_sector) = LOWER(?)
            ORDER BY s.company_id
            """,
            (sector,),
        ).fetchall()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Sector '{sector}' not found.",
            )

        return {
            "sector": rows[0]["broad_sector"],
            "count": len(rows),
            "companies": [dict(row) for row in rows],
        }

    finally:
        conn.close()
