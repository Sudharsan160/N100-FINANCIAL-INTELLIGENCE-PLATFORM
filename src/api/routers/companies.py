import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter()

ROOT = Path(__file__).resolve().parents[3]

DB_PATH = ROOT / "nifty100.db"
TEARSHEET_DIR = ROOT / "reports" / "tearsheets"

YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------------


def get_connection():
    """Create a SQLite connection using dictionary-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_sector_info(conn, company_id):
    """Return sector and market-cap information for a company."""
    row = conn.execute(
        """
        SELECT
            broad_sector,
            sub_sector,
            index_weight_pct,
            market_cap_category
        FROM sectors
        WHERE company_id = ?
        LIMIT 1
        """,
        (company_id,),
    ).fetchone()

    if not row:
        return {
            "broad_sector": None,
            "sub_sector": None,
            "index_weight_pct": None,
            "market_cap_category": None,
        }

    return dict(row)


def get_company(conn, ticker):
    """Return a company using companies.id as the ticker."""
    row = conn.execute(
        """
        SELECT *
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()

    return row


def get_latest_ratios(conn, company_id):
    """Return the latest financial-ratio record."""
    row = conn.execute(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 1
        """,
        (company_id,),
    ).fetchone()

    if not row:
        return None

    return dict(row)


def calculate_cagr(start_value, end_value, years):
    """Calculate CAGR as a percentage."""
    try:
        start_value = float(start_value)
        end_value = float(end_value)

        if years <= 0 or start_value <= 0 or end_value < 0:
            return None

        result = ((end_value / start_value) ** (1 / years) - 1) * 100

        return result

    except (
        TypeError,
        ValueError,
        ZeroDivisionError,
    ):
        return None


def add_derived_kpis(conn, company_id, ratios):
    """Add five-year revenue and PAT CAGR where available."""
    if ratios is None:
        return None

    result = dict(ratios)

    rows = conn.execute(
        """
        SELECT
            year,
            sales,
            net_profit
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    if not rows:
        return result

    latest = rows[-1]

    try:
        target_year = int(latest["year"]) - 5
    except (TypeError, ValueError):
        return result

    earlier = next(
        (row for row in rows if row["year"] == target_year),
        None,
    )

    if earlier is None:
        return result

    revenue_cagr = calculate_cagr(
        earlier["sales"],
        latest["sales"],
        5,
    )

    pat_cagr = calculate_cagr(
        earlier["net_profit"],
        latest["net_profit"],
        5,
    )

    result["revenue_cagr_5yr"] = revenue_cagr
    result["pat_cagr_5yr"] = pat_cagr

    return result


def validate_year_month(value, parameter_name):
    """Validate a YYYY-MM query parameter and return its year."""
    if value is None:
        return None

    if not YEAR_MONTH_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=(f"{parameter_name} must use YYYY-MM format."),
        )

    return int(value[:4])


# ---------------------------------------------------------
# COMPANY LIST
# ---------------------------------------------------------


@router.get("/companies")
def list_companies(
    sector: str | None = Query(
        default=None,
        description="Filter by broad sector.",
    ),
    market_cap_category: str | None = Query(
        default=None,
        description="Filter by market-cap category.",
    ),
    search: str | None = Query(
        default=None,
        description="Search ticker or company name.",
    ),
):
    """Return all companies with sector, ROE and ROCE."""
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                id,
                company_name,
                roe_percentage,
                roce_percentage
            FROM companies
            ORDER BY id
            """).fetchall()

        results = []

        for row in rows:
            company = dict(row)

            ticker = company["id"]
            name = company["company_name"]

            sector_info = get_sector_info(
                conn,
                ticker,
            )

            # Sector filter.
            if sector:
                broad_sector = sector_info["broad_sector"] or ""

                if broad_sector.lower() != sector.lower():
                    continue

            # Market-cap filter.
            if market_cap_category:
                category = sector_info["market_cap_category"] or ""

                if category.lower() != (market_cap_category.lower()):
                    continue

            # Search filter.
            if search:
                search_text = (f"{ticker} {name}").lower()

                if search.lower() not in search_text:
                    continue

            results.append(
                {
                    "id": ticker,
                    "ticker": ticker,
                    "name": name,
                    "broad_sector": (sector_info["broad_sector"]),
                    "sub_sector": (sector_info["sub_sector"]),
                    "market_cap_category": (sector_info["market_cap_category"]),
                    "roe": company["roe_percentage"],
                    "roce": company["roce_percentage"],
                }
            )

        return {
            "count": len(results),
            "companies": results,
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# COMPANY PROFILE
# ---------------------------------------------------------


@router.get("/companies/{ticker}")
def company_profile(ticker: str):
    """Return complete company information and latest KPIs."""
    conn = get_connection()

    try:
        company = get_company(
            conn,
            ticker,
        )

        if not company:
            raise HTTPException(
                status_code=404,
                detail=(f"Company '{ticker}' not found."),
            )

        company_data = dict(company)

        company_id = company_data["id"]

        sector_info = get_sector_info(
            conn,
            company_id,
        )

        latest_kpis = get_latest_ratios(
            conn,
            company_id,
        )

        latest_kpis = add_derived_kpis(
            conn,
            company_id,
            latest_kpis,
        )

        return {
            "company": company_data,
            "sector": sector_info,
            "latest_kpis": latest_kpis,
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# P&L
# ---------------------------------------------------------


@router.get("/companies/{ticker}/pl")
def company_profit_and_loss(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Start year in YYYY-MM format.",
    ),
    to_year: str | None = Query(
        default=None,
        description="End year in YYYY-MM format.",
    ),
):
    """Return company profit-and-loss history."""
    from_year_int = validate_year_month(
        from_year,
        "from_year",
    )

    to_year_int = validate_year_month(
        to_year,
        "to_year",
    )

    if (
        from_year_int is not None
        and to_year_int is not None
        and from_year_int > to_year_int
    ):
        raise HTTPException(
            status_code=400,
            detail=("from_year cannot be greater than to_year."),
        )

    conn = get_connection()

    try:
        company = get_company(
            conn,
            ticker,
        )

        if not company:
            raise HTTPException(
                status_code=404,
                detail=(f"Company '{ticker}' not found."),
            )

        company_id = company["id"]

        query = """
            SELECT *
            FROM profitandloss
            WHERE company_id = ?
        """

        params = [company_id]

        if from_year_int is not None:
            query += " AND year >= ?"
            params.append(from_year_int)

        if to_year_int is not None:
            query += " AND year <= ?"
            params.append(to_year_int)

        query += " ORDER BY year"

        rows = conn.execute(
            query,
            params,
        ).fetchall()

        return {
            "ticker": ticker.upper(),
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# BALANCE SHEET
# ---------------------------------------------------------


@router.get("/companies/{ticker}/bs")
def company_balance_sheet(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Start year in YYYY-MM format.",
    ),
    to_year: str | None = Query(
        default=None,
        description="End year in YYYY-MM format.",
    ),
):
    """Return company balance-sheet history."""
    from_year_int = validate_year_month(
        from_year,
        "from_year",
    )

    to_year_int = validate_year_month(
        to_year,
        "to_year",
    )

    if (
        from_year_int is not None
        and to_year_int is not None
        and from_year_int > to_year_int
    ):
        raise HTTPException(
            status_code=400,
            detail=("from_year cannot be greater than to_year."),
        )

    conn = get_connection()

    try:
        company = get_company(
            conn,
            ticker,
        )

        if not company:
            raise HTTPException(
                status_code=404,
                detail=(f"Company '{ticker}' not found."),
            )

        company_id = company["id"]

        query = """
            SELECT *
            FROM balancesheet
            WHERE company_id = ?
        """

        params = [company_id]

        if from_year_int is not None:
            query += " AND year >= ?"
            params.append(from_year_int)

        if to_year_int is not None:
            query += " AND year <= ?"
            params.append(to_year_int)

        query += " ORDER BY year"

        rows = conn.execute(
            query,
            params,
        ).fetchall()

        return {
            "ticker": ticker.upper(),
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# CASH FLOW
# ---------------------------------------------------------


@router.get("/companies/{ticker}/cashflow")
def company_cashflow(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Start year in YYYY-MM format.",
    ),
    to_year: str | None = Query(
        default=None,
        description="End year in YYYY-MM format.",
    ),
):
    """Return company cash-flow history."""
    from_year_int = validate_year_month(
        from_year,
        "from_year",
    )

    to_year_int = validate_year_month(
        to_year,
        "to_year",
    )

    if (
        from_year_int is not None
        and to_year_int is not None
        and from_year_int > to_year_int
    ):
        raise HTTPException(
            status_code=400,
            detail=("from_year cannot be greater than to_year."),
        )

    conn = get_connection()

    try:
        company = get_company(
            conn,
            ticker,
        )

        if not company:
            raise HTTPException(
                status_code=404,
                detail=(f"Company '{ticker}' not found."),
            )

        company_id = company["id"]

        query = """
            SELECT *
            FROM cashflow
            WHERE company_id = ?
        """

        params = [company_id]

        if from_year_int is not None:
            query += " AND year >= ?"
            params.append(from_year_int)

        if to_year_int is not None:
            query += " AND year <= ?"
            params.append(to_year_int)

        query += " ORDER BY year"

        rows = conn.execute(
            query,
            params,
        ).fetchall()

        return {
            "ticker": ticker.upper(),
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# RATIOS
# ---------------------------------------------------------


@router.get("/companies/{ticker}/ratios")
def company_ratios(
    ticker: str,
    year: int | None = Query(
        default=None,
        ge=1900,
        le=2100,
        description="Optional financial year.",
    ),
):
    """Return company financial ratios."""
    conn = get_connection()

    try:
        company = get_company(
            conn,
            ticker,
        )

        if not company:
            raise HTTPException(
                status_code=404,
                detail=(f"Company '{ticker}' not found."),
            )

        company_id = company["id"]

        if year is None:
            rows = conn.execute(
                """
                SELECT *
                FROM financial_ratios
                WHERE company_id = ?
                ORDER BY year
                """,
                (company_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT *
                FROM financial_ratios
                WHERE company_id = ?
                  AND year = ?
                ORDER BY year
                """,
                (
                    company_id,
                    year,
                ),
            ).fetchall()

        return {
            "ticker": ticker.upper(),
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()


# ---------------------------------------------------------
# TEARSHEET PDF
# ---------------------------------------------------------


@router.get(
    "/companies/{ticker}/tearsheet",
    response_class=FileResponse,
)
def company_tearsheet(ticker: str):
    """Return the company's PDF tearsheet."""
    ticker = ticker.upper()

    pdf_path = TEARSHEET_DIR / f"{ticker}.pdf"

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(f"Tearsheet for '{ticker}' " "was not found."),
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{ticker}.pdf",
    )
