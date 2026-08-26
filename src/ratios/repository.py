from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.ratios.calculator import calculate_ratio_row, deduplicate_records


DB_PATH = Path("nifty100.db")


RATIO_COLUMNS = [
    "company_id",
    "year",

    # Day 08
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "capex_cr",
    "earnings_per_share",
    "book_value_per_share",
    "dividend_payout_ratio_pct",
    "total_debt_cr",
    "cash_from_operations_cr",

    # Day 09
    "return_on_assets_pct",
    "pretax_margin_pct",
    "operating_cash_flow_margin_pct",
    "cash_flow_to_net_profit",
    "debt_ratio",
    "equity_ratio",
    "financial_leverage",
    "revenue_growth_pct",
    "operating_profit_growth_pct",
    "net_profit_growth_pct",
    "eps_growth_pct",

    # Day 11 — Cash Flow & Capital Allocation
    "cfo_to_total_debt",
    "free_cash_flow_margin_pct",
    "investing_cash_flow_to_cfo",
    "financing_cash_flow_to_cfo",
    "cash_conversion_ratio",
    "capital_expenditure_intensity_pct",
]


def fetch_grouped_records(
    conn: sqlite3.Connection,
    table_name: str,
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    """Fetch table rows grouped by company_id and year."""

    query = f"""
        SELECT *
        FROM "{table_name}"
        WHERE company_id IS NOT NULL
          AND year IS NOT NULL
        ORDER BY company_id, year, id
    """

    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}

    cursor = conn.execute(query)

    for row in cursor.fetchall():
        record = dict(row)

        key = (
            str(record["company_id"]),
            int(record["year"]),
        )

        groups.setdefault(key, []).append(record)

    return groups


def canonicalize_groups(
    groups: dict[tuple[str, int], list[dict[str, Any]]],
) -> dict[tuple[str, int], dict[str, Any]]:
    """Reduce each company/year group to one deterministic source record."""

    canonical: dict[tuple[str, int], dict[str, Any]] = {}

    for key, records in groups.items():
        cleaned = deduplicate_records(records)

        if cleaned:
            canonical[key] = cleaned[0]

    return canonical


def create_ratio_unique_index(
    conn: sqlite3.Connection,
) -> None:
    """
    Create a unique index after the table has been cleaned.

    This prevents future duplicate company/year ratio rows.
    """
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_financial_ratios_company_year
        ON financial_ratios(company_id, year)
    """)


def upsert_ratio_row(
    conn: sqlite3.Connection,
    ratio: dict[str, Any],
) -> None:
    """Insert or update one canonical ratio row."""

    columns = ", ".join(RATIO_COLUMNS)

    placeholders = ", ".join(
        ["?"] * len(RATIO_COLUMNS)
    )

    update_columns = [
        column
        for column in RATIO_COLUMNS
        if column not in {"company_id", "year"}
    ]

    updates = ", ".join(
        f"{column}=excluded.{column}"
        for column in update_columns
    )

    values = [
        ratio.get(column)
        for column in RATIO_COLUMNS
    ]

    conn.execute(
        f"""
        INSERT INTO financial_ratios ({columns})
        VALUES ({placeholders})
        ON CONFLICT(company_id, year)
        DO UPDATE SET
            {updates}
        """,
        values,
    )


def build_ratio_rows(
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Build one ratio row per company/year supported by source data."""

    pnl_groups = canonicalize_groups(
        fetch_grouped_records(conn, "profitandloss")
    )

    bs_groups = canonicalize_groups(
        fetch_grouped_records(conn, "balancesheet")
    )

    cf_groups = canonicalize_groups(
        fetch_grouped_records(conn, "cashflow")
    )

    companies = {
        row["id"]: row["face_value"]
        for row in conn.execute(
            "SELECT id, face_value FROM companies ORDER BY id"
        ).fetchall()
    }

    ratio_rows: list[dict[str, Any]] = []

    available_keys = set(pnl_groups) | set(bs_groups)

    for company_id in companies:
        company_keys = sorted(
            key
            for key in available_keys
            if key[0] == company_id
        )

        pnl_company_keys = sorted(
            key
            for key in pnl_groups
            if key[0] == company_id
        )

        for key in company_keys:
            profit_loss = pnl_groups.get(key)
            balance_sheet = bs_groups.get(key)
            cash_flow = cf_groups.get(key)

            if profit_loss is None and balance_sheet is None:
                continue

            if profit_loss is None:
                profit_loss = {
                    "company_id": company_id,
                    "year": key[1],
                    "sales": None,
                    "operating_profit": None,
                    "profit_before_tax": None,
                    "net_profit": None,
                    "interest": None,
                    "eps": None,
                    "dividend_payout": None,
                }

            if balance_sheet is None:
                balance_sheet = {
                    "company_id": company_id,
                    "year": key[1],
                    "equity_capital": None,
                    "reserves": None,
                    "borrowings": None,
                    "total_assets": None,
                }

            profit_loss["face_value"] = companies[company_id]

            previous_profit_loss = None

            if key in pnl_company_keys:
                current_position = pnl_company_keys.index(key)

                if current_position > 0:
                    previous_key = pnl_company_keys[
                        current_position - 1
                    ]
                    previous_profit_loss = pnl_groups.get(
                        previous_key
                    )

            ratio_rows.append(
                calculate_ratio_row(
                    profit_loss,
                    balance_sheet,
                    cash_flow,
                    previous_profit_loss,
                )
            )

    return ratio_rows


def rebuild_financial_ratios(
    db_path: str | Path = DB_PATH,
) -> int:
    """
    Rebuild the financial_ratios table from canonical source data.

    Existing ratio rows are replaced only after source rows have been
    canonicalized and ratio rows calculated successfully.
    """

    db_path = Path(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        ratio_rows = build_ratio_rows(conn)

        # Replace the old ratio dataset.
        conn.execute("DELETE FROM financial_ratios")

        for ratio in ratio_rows:
            columns = ", ".join(RATIO_COLUMNS)
            placeholders = ", ".join(["?"] * len(RATIO_COLUMNS))

            values = [
                ratio.get(column)
                for column in RATIO_COLUMNS
            ]

            conn.execute(
                f"""
                INSERT INTO financial_ratios ({columns})
                VALUES ({placeholders})
                """,
                values,
            )

        create_ratio_unique_index(conn)

        conn.commit()

        return len(ratio_rows)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()