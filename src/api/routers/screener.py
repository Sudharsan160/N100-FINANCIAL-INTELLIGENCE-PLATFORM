from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def get_connection():
    """Create a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_cagr(start_value, end_value, years=5):
    """Calculate CAGR percentage for positive financial values."""
    try:
        start_value = float(start_value)
        end_value = float(end_value)

        if start_value <= 0 or end_value < 0:
            return None

        return (((end_value / start_value) ** (1 / years)) - 1) * 100

    except (TypeError, ValueError, ZeroDivisionError):
        return None


def get_latest_cagr(conn, company_id):
    """Calculate latest 5-year revenue, PAT, and FCF CAGR values."""
    rows = conn.execute(
        """
        SELECT year, sales, net_profit
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    ratio_rows = conn.execute(
        """
        SELECT year, free_cash_flow_cr
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    revenue_cagr = None
    pat_cagr = None
    fcf_cagr = None

    if len(rows) >= 6:
        latest = rows[-1]

        earlier = next(
            (
                row
                for row in rows
                if row["year"] == latest["year"] - 5
            ),
            None,
        )

        if earlier:
            revenue_cagr = calculate_cagr(
                earlier["sales"],
                latest["sales"],
            )

            pat_cagr = calculate_cagr(
                earlier["net_profit"],
                latest["net_profit"],
            )

    if len(ratio_rows) >= 6:
        latest = ratio_rows[-1]

        earlier = next(
            (
                row
                for row in ratio_rows
                if row["year"] == latest["year"] - 5
            ),
            None,
        )

        if earlier:
            fcf_cagr = calculate_cagr(
                earlier["free_cash_flow_cr"],
                latest["free_cash_flow_cr"],
            )

    return revenue_cagr, pat_cagr, fcf_cagr


@router.get("/screener")
def screener(
    min_roe: float | None = Query(None),
    max_de: float | None = Query(None),
    min_fcf: float | None = Query(None),
    sector: str | None = Query(None),
    min_rev_cagr_5yr: float | None = Query(None),
    min_pat_cagr_5yr: float | None = Query(None),
    max_pe: float | None = Query(None),
    min_opm: float | None = Query(None),
    max_pb: float | None = Query(None),
    min_dividend: float | None = Query(None),
    min_icr: float | None = Query(None),
):
    """Screen companies using latest financial and valuation metrics."""

    # ---------------------------------------------------------
    # Parameter validation
    # ---------------------------------------------------------
    if min_roe is not None and min_roe < -10000:
        raise HTTPException(
            status_code=400,
            detail="Invalid min_roe.",
        )

    if max_de is not None and max_de < 0:
        raise HTTPException(
            status_code=400,
            detail="max_de cannot be negative.",
        )

    if min_fcf is not None and not isinstance(min_fcf, (int, float)):
        raise HTTPException(
            status_code=400,
            detail="Invalid min_fcf.",
        )

    if min_rev_cagr_5yr is not None and min_rev_cagr_5yr < -100:
        raise HTTPException(
            status_code=400,
            detail="Invalid min_rev_cagr_5yr.",
        )

    if min_pat_cagr_5yr is not None and min_pat_cagr_5yr < -100:
        raise HTTPException(
            status_code=400,
            detail="Invalid min_pat_cagr_5yr.",
        )

    if max_pe is not None and max_pe < 0:
        raise HTTPException(
            status_code=400,
            detail="max_pe cannot be negative.",
        )

    if min_opm is not None and min_opm < -100:
        raise HTTPException(
            status_code=400,
            detail="min_opm cannot be below -100.",
        )

    if max_pb is not None and max_pb < 0:
        raise HTTPException(
            status_code=400,
            detail="max_pb cannot be negative.",
        )

    if min_dividend is not None and min_dividend < 0:
        raise HTTPException(
            status_code=400,
            detail="min_dividend cannot be negative.",
        )

    if min_icr is not None and min_icr < 0:
        raise HTTPException(
            status_code=400,
            detail="min_icr cannot be negative.",
        )

    conn = get_connection()

    try:
        # -----------------------------------------------------
        # Company master data
        # -----------------------------------------------------
        companies = conn.execute(
            """
            SELECT
                id,
                company_name,
                roe_percentage,
                roce_percentage
            FROM companies
            ORDER BY id
            """
        ).fetchall()

        results = []

        # -----------------------------------------------------
        # Evaluate each company
        # -----------------------------------------------------
        for company in companies:
            company_id = company["id"]

            sector_row = conn.execute(
                """
                SELECT
                    broad_sector,
                    sub_sector,
                    market_cap_category
                FROM sectors
                WHERE company_id = ?
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()

            ratios = conn.execute(
                """
                SELECT *
                FROM financial_ratios
                WHERE company_id = ?
                ORDER BY year DESC
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()

            market = conn.execute(
                """
                SELECT *
                FROM market_cap
                WHERE company_id = ?
                ORDER BY year DESC
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()

            if ratios is None:
                continue

            revenue_cagr, pat_cagr, _ = get_latest_cagr(
                conn,
                company_id,
            )

            broad_sector = (
                sector_row["broad_sector"]
                if sector_row is not None
                else None
            )

            sub_sector = (
                sector_row["sub_sector"]
                if sector_row is not None
                else None
            )

            market_cap_category = (
                sector_row["market_cap_category"]
                if sector_row is not None
                else None
            )

            roe = ratios["return_on_equity_pct"]
            de = ratios["debt_to_equity"]
            fcf = ratios["free_cash_flow_cr"]
            opm = ratios["operating_profit_margin_pct"]
            icr = ratios["interest_coverage"]

            pe = market["pe_ratio"] if market else None
            pb = market["pb_ratio"] if market else None
            dividend = (
                market["dividend_yield_pct"]
                if market
                else None
            )

            # -------------------------------------------------
            # Financial-sector D/E carve-out
            #
            # Keep this aligned with the existing dashboard
            # integration test: financial companies are exempt
            # from the max D/E filter.
            # -------------------------------------------------
            is_financials = (
                broad_sector is not None
                and broad_sector.strip().casefold() == "financials"
            )

            # -------------------------------------------------
            # Apply filters
            # -------------------------------------------------
            if min_roe is not None and (
                roe is None or roe < min_roe
            ):
                continue

            if max_de is not None and not is_financials and (
                de is None or de > max_de
            ):
                continue

            if min_fcf is not None and (
                fcf is None or fcf < min_fcf
            ):
                continue

            if sector and (
                broad_sector is None
                or broad_sector.strip().casefold()
                != sector.strip().casefold()
            ):
                continue

            if min_rev_cagr_5yr is not None and (
                revenue_cagr is None
                or revenue_cagr < min_rev_cagr_5yr
            ):
                continue

            if min_pat_cagr_5yr is not None and (
                pat_cagr is None
                or pat_cagr < min_pat_cagr_5yr
            ):
                continue

            if max_pe is not None and (
                pe is None or pe > max_pe
            ):
                continue

            if min_opm is not None and (
                opm is None or opm < min_opm
            ):
                continue

            if max_pb is not None and (
                pb is None or pb > max_pb
            ):
                continue

            if min_dividend is not None and (
                dividend is None or dividend < min_dividend
            ):
                continue

            if min_icr is not None and (
                icr is None or icr < min_icr
            ):
                continue

            # -------------------------------------------------
            # Result row
            # -------------------------------------------------
            results.append(
                {
                    "ticker": company_id,
                    "company_name": company["company_name"],
                    "broad_sector": broad_sector,
                    "sub_sector": sub_sector,
                    "market_cap_category": market_cap_category,
                    "roe": roe,
                    "debt_to_equity": de,
                    "free_cash_flow_cr": fcf,
                    "revenue_cagr_5yr": revenue_cagr,
                    "pat_cagr_5yr": pat_cagr,
                    "operating_profit_margin_pct": opm,
                    "pe_ratio": pe,
                    "pb_ratio": pb,
                    "dividend_yield_pct": dividend,
                    "interest_coverage": icr,
                }
            )

        return {
            "count": len(results),
            "data": results,
        }

    finally:
        conn.close()