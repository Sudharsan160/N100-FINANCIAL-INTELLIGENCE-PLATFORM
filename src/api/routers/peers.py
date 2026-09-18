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


@router.get("/peers/{group_name}")
def peer_group(group_name: str):
    """Return companies and percentile metrics for a peer group."""

    conn = get_connection()

    try:
        members = conn.execute(
            """
            SELECT
                peer_group_name,
                company_id,
                is_benchmark
            FROM peer_groups
            WHERE LOWER(peer_group_name) = LOWER(?)
            ORDER BY company_id
            """,
            (group_name,),
        ).fetchall()

        if not members:
            raise HTTPException(
                status_code=404,
                detail=(f"Peer group '{group_name}' not found."),
            )

        percentiles = conn.execute(
            """
            SELECT
                company_id,
                peer_group_name,
                metric,
                value,
                percentile_rank,
                year
            FROM peer_percentiles
            WHERE LOWER(peer_group_name) = LOWER(?)
            ORDER BY company_id, metric
            """,
            (group_name,),
        ).fetchall()

        return {
            "peer_group": group_name,
            "company_count": len(members),
            "companies": [dict(row) for row in members],
            "percentiles": [dict(row) for row in percentiles],
        }

    finally:
        conn.close()


@router.get("/companies/{ticker}/peers/compare")
def compare_peers(ticker: str):
    """
    Compare a company with its peer-group average and benchmark
    across eight latest-year metrics.
    """

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

        membership = conn.execute(
            """
            SELECT
                peer_group_name,
                is_benchmark
            FROM peer_groups
            WHERE UPPER(company_id) = UPPER(?)
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()

        if not membership:
            raise HTTPException(
                status_code=404,
                detail=(f"No peer group found for '{ticker}'."),
            )

        group_name = membership["peer_group_name"]

        group_members = conn.execute(
            """
            SELECT company_id, is_benchmark
            FROM peer_groups
            WHERE peer_group_name = ?
            """,
            (group_name,),
        ).fetchall()

        metrics = {
            "ROE": "return_on_equity_pct",
            "D/E": "debt_to_equity",
            "Revenue Growth": "revenue_growth_pct",
            "Net Margin": "net_profit_margin_pct",
            "OPM": "operating_profit_margin_pct",
            "Interest Coverage": "interest_coverage",
            "FCF Margin": "free_cash_flow_margin_pct",
            "CapEx Intensity": ("capital_expenditure_intensity_pct"),
        }

        company_ids = [row["company_id"] for row in group_members]

        placeholders = ",".join("?" for _ in company_ids)

        latest_rows = conn.execute(
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

        latest = {row["company_id"]: dict(row) for row in latest_rows}

        subject = latest.get(ticker.upper())

        if not subject:
            raise HTTPException(
                status_code=404,
                detail=(f"No latest financial ratios for '{ticker}'."),
            )

        comparison = []

        for label, column in metrics.items():
            company_value = subject.get(column)

            peer_values = [
                row.get(column)
                for company_id, row in latest.items()
                if company_id.upper() != ticker.upper() and row.get(column) is not None
            ]

            benchmark_value = None

            benchmark_ids = {
                row["company_id"] for row in group_members if row["is_benchmark"] == 1
            }

            for benchmark_id in benchmark_ids:
                benchmark_row = latest.get(benchmark_id)

                if benchmark_row:
                    benchmark_value = benchmark_row.get(column)
                    break

            peer_average = sum(peer_values) / len(peer_values) if peer_values else None

            comparison.append(
                {
                    "metric": label,
                    "company_value": company_value,
                    "peer_average": peer_average,
                    "benchmark": benchmark_value,
                }
            )

        return {
            "ticker": ticker.upper(),
            "company_name": company["company_name"],
            "peer_group": group_name,
            "comparison": comparison,
        }

    finally:
        conn.close()
