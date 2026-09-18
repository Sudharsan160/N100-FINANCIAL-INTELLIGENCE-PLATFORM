import sqlite3
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/portfolio/stats")
def portfolio_stats():
    """Return portfolio-wide latest KPI statistics."""

    conn = get_connection()

    try:
        companies = conn.execute("""
            SELECT id
            FROM companies
            ORDER BY id
            """).fetchall()

        company_ids = [row["id"] for row in companies]

        if not company_ids:
            return {
                "company_count": 0,
                "stats": [],
            }

        placeholders = ",".join("?" for _ in company_ids)

        rows = conn.execute(
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

        metrics = [
            "return_on_equity_pct",
            "debt_to_equity",
            "revenue_growth_pct",
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "free_cash_flow_margin_pct",
            "cash_flow_to_net_profit",
            "capital_expenditure_intensity_pct",
        ]

        stats = []

        for metric in metrics:
            values = sorted(
                [float(row[metric]) for row in rows if row[metric] is not None]
            )

            if not values:
                continue

            series = values
            n = len(series)

            def percentile(p, series=series, n=n):
                if n == 1:
                    return series[0]

                index = (n - 1) * p
                lower = int(index)
                upper = min(
                    lower + 1,
                    n - 1,
                )
                fraction = index - lower

                return series[lower] + (series[upper] - series[lower]) * fraction

            mean = sum(series) / n

            variance = sum((x - mean) ** 2 for x in series) / n

            stats.append(
                {
                    "kpi": metric,
                    "P10": percentile(0.10),
                    "P25": percentile(0.25),
                    "P50": percentile(0.50),
                    "P75": percentile(0.75),
                    "P90": percentile(0.90),
                    "Mean": mean,
                    "Std": variance**0.5,
                    "sample_count": n,
                }
            )

        return {
            "company_count": len(company_ids),
            "latest_ratio_rows": len(rows),
            "stats": stats,
        }

    finally:
        conn.close()
