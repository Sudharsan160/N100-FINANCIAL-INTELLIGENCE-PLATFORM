from pathlib import Path
import os
import sqlite3
from typing import Optional

import pandas as pd
import streamlit as st


# Project root:
# C:\COLLEGE\Projects\N100 FINANCIAL INTELLIGENCE PLATFORM
ROOT_DIR = Path(__file__).resolve().parents[3]

DB_PATH = Path(
    os.getenv("DB_PATH", str(ROOT_DIR / "nifty100.db"))
)


def _get_connection() -> sqlite3.Connection:
    """Create a connection to the SQLite database."""
    return sqlite3.connect(str(DB_PATH))


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """Return all companies."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name,
                company_logo,
                chart_link,
                about_company,
                website,
                nse_profile,
                bse_profile,
                face_value,
                book_value,
                roce_percentage,
                roe_percentage
            FROM companies
            ORDER BY company_name
            """,
            conn,
        )


@st.cache_data(ttl=600)
def get_ratios(
    ticker: str,
    year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Return financial ratios for a company.

    `ticker` refers to companies.id, which is the identifier used
    as company_id throughout the database.
    """
    query = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
    """
    params = [ticker]

    if year is not None:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY year"

    with _get_connection() as conn:
        return pd.read_sql_query(
            query,
            conn,
            params=params,
        )


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    """Return profit and loss history for a company."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM profitandloss
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=[ticker],
        )


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    """Return balance sheet history for a company."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM balancesheet
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=[ticker],
        )


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    """Return cash flow history for a company."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM cashflow
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=[ticker],
        )


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """Return company sector and sub-sector mappings."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                company_id,
                broad_sector,
                sub_sector,
                index_weight_pct,
                market_cap_category
            FROM sectors
            ORDER BY broad_sector, sub_sector, company_id
            """,
            conn,
        )


@st.cache_data(ttl=600)
def get_peers(group_name: str) -> pd.DataFrame:
    """Return companies belonging to a peer group."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                pg.peer_group_name,
                pg.company_id,
                pg.is_benchmark,
                c.company_name
            FROM peer_groups pg
            LEFT JOIN companies c
                ON c.id = pg.company_id
            WHERE pg.peer_group_name = ?
            ORDER BY
                pg.is_benchmark DESC,
                c.company_name
            """,
            conn,
            params=[group_name],
        )


@st.cache_data(ttl=600)
def get_valuation(ticker: str) -> pd.DataFrame:
    """Return valuation and supporting financial data for a company."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                mc.company_id,
                mc.year,
                mc.market_cap_crore,
                mc.enterprise_value_crore,
                mc.pe_ratio,
                mc.pb_ratio,
                mc.ev_ebitda,
                mc.dividend_yield_pct,
                fr.free_cash_flow_cr,
                s.broad_sector,
                s.sub_sector
            FROM market_cap mc
            LEFT JOIN financial_ratios fr
                ON fr.company_id = mc.company_id
               AND fr.year = mc.year
            LEFT JOIN sectors s
                ON s.company_id = mc.company_id
            WHERE mc.company_id = ?
            ORDER BY mc.year
            """,
            conn,
            params=[ticker],
        )


@st.cache_data(ttl=600)
def get_reports(ticker: str) -> pd.DataFrame:
    """Return annual report records for a company."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                annual_report
            FROM documents
            WHERE company_id = ?
            ORDER BY year DESC
            """,
            conn,
            params=[ticker],
        )


@st.cache_data(ttl=600)
def get_pros_cons(ticker: str) -> pd.DataFrame:
    """Return pros and cons for a company."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                company_id,
                pros,
                cons
            FROM prosandcons
            WHERE company_id = ?
            """,
            conn,
            params=[ticker],
        )


@st.cache_data(ttl=600)
def get_stock_prices(ticker: str) -> pd.DataFrame:
    """Return stock price history for a company."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM stock_prices
            WHERE company_id = ?
            ORDER BY year
            """,
            conn,
            params=[ticker],
        )


@st.cache_data(ttl=600)
def get_peer_percentiles(group_name: str) -> pd.DataFrame:
    """Return calculated peer percentiles for a peer group."""
    with _get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM peer_percentiles
            WHERE peer_group_name = ?
            """,
            conn,
            params=[group_name],
        )


def database_exists() -> bool:
    """Check whether the configured SQLite database exists."""
    return DB_PATH.exists()