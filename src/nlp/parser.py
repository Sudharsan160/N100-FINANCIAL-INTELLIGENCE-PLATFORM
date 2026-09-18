from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

from src.analytics.cagr import calculate_cagr

ROOT_DIR = Path(__file__).resolve().parents[2]
ANALYSIS_PATH = ROOT_DIR / "data" / "raw" / "analysis.xlsx"
DB_PATH = ROOT_DIR / "nifty100.db"
OUTPUT_DIR = ROOT_DIR / "output"

PARSED_PATH = OUTPUT_DIR / "analysis_parsed.csv"
FAILURES_PATH = OUTPUT_DIR / "parse_failures.csv"


# Required pattern from the Sprint 5 specification.
# Examples:
#   10 Years: 21%
#   5 Years: 24%
#   3 Years: 17%
CAGR_PATTERN = re.compile(
    r"(\d+)\s*Years?\s*:?\s*([+-]?\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


TARGET_COLUMNS = {
    "compounded_sales_growth": "sales_cagr",
    "compounded_profit_growth": "profit_cagr",
    "stock_price_cagr": "stock_price_cagr",
    "roe": "roe",
}


def load_analysis() -> pd.DataFrame:
    """Load and normalize the analysis.xlsx structure."""

    raw = pd.read_excel(ANALYSIS_PATH)

    # The workbook has a title row above the real header.
    if "company_id" not in raw.columns:
        if len(raw) < 2:
            raise ValueError("analysis.xlsx does not contain a usable header row.")

        raw = pd.read_excel(
            ANALYSIS_PATH,
            header=1,
        )

    raw.columns = [str(column).strip() for column in raw.columns]

    required = [
        "company_id",
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    ]

    missing = [column for column in required if column not in raw.columns]

    if missing:
        raise ValueError(f"Missing required columns in analysis.xlsx: {missing}")

    return raw[required].copy()


def parse_metric_text(value) -> tuple[int | None, float | None]:
    """Extract period in years and percentage from a CAGR-style string."""

    if pd.isna(value):
        return None, None

    text = str(value).strip()

    match = CAGR_PATTERN.search(text)

    if not match:
        return None, None

    period_years = int(match.group(1))
    value_pct = float(match.group(2))

    return period_years, value_pct


def parse_analysis() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse the four target fields into a structured table."""

    source = load_analysis()

    parsed_rows: list[dict] = []
    failure_rows: list[dict] = []

    for row_index, row in source.iterrows():

        company_id = str(row["company_id"]).strip()

        for source_column, metric_type in TARGET_COLUMNS.items():

            raw_text = row[source_column]

            period_years, value_pct = parse_metric_text(raw_text)

            if period_years is None or value_pct is None:
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "source_column": source_column,
                        "raw_text": (None if pd.isna(raw_text) else str(raw_text)),
                        "row_number": int(row_index) + 2,
                        "failure_reason": "Pattern not matched",
                    }
                )
                continue

            parsed_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    return (
        pd.DataFrame(parsed_rows),
        pd.DataFrame(failure_rows),
    )


def load_financial_history() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load P&L history used for independent CAGR cross-validation."""

    with sqlite3.connect(str(DB_PATH)) as conn:

        pl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales,
                net_profit
            FROM profitandloss
            ORDER BY company_id, year
            """,
            conn,
        )

        bs = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                total_assets,
                borrowings
            FROM balancesheet
            ORDER BY company_id, year
            """,
            conn,
        )

    return pl, bs


def computed_cagr_for_company(
    history: pd.DataFrame,
    company_id: str,
    metric: str,
    period_years: int,
) -> float | None:
    """
    Compute CAGR using the same calculate_cagr() function as the Ratio Engine.

    For a requested N-year CAGR:
      start = latest year - N
      end   = latest year
    """

    subset = history[history["company_id"].astype(str) == str(company_id)].copy()

    if subset.empty:
        return None

    subset["year"] = pd.to_numeric(
        subset["year"],
        errors="coerce",
    )

    subset = subset.dropna(subset=["year"]).sort_values("year")

    if subset.empty:
        return None

    latest_year = int(subset["year"].max())
    start_year = latest_year - int(period_years)

    start_row = subset[subset["year"] == start_year]

    end_row = subset[subset["year"] == latest_year]

    if start_row.empty or end_row.empty:
        return None

    start_value = start_row.iloc[-1][metric]
    end_value = end_row.iloc[-1][metric]

    return calculate_cagr(
        start_value,
        end_value,
        period_years,
    )


def cross_validate(
    parsed: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cross-validate sales/profit parsed CAGRs against the Ratio Engine CAGR.

    Stock-price CAGR is not cross-validated because the existing Ratio
    Engine CAGR functions operate on revenue, profit, and EPS, while ROE
    is a level metric rather than a CAGR metric.
    """

    if parsed.empty:
        return parsed.copy()

    pl, _ = load_financial_history()

    sales_history = pl[["company_id", "year", "sales"]].copy()

    profit_history = pl[["company_id", "year", "net_profit"]].copy()

    comparison_rows: list[dict] = []

    for _, row in parsed.iterrows():

        metric_type = row["metric_type"]
        company_id = str(row["company_id"])
        period_years = int(row["period_years"])
        parsed_value = float(row["value_pct"])

        computed_value = None

        if metric_type == "sales_cagr":
            computed_value = computed_cagr_for_company(
                sales_history,
                company_id,
                "sales",
                period_years,
            )

        elif metric_type == "profit_cagr":
            computed_value = computed_cagr_for_company(
                profit_history,
                company_id,
                "net_profit",
                period_years,
            )

        # For stock-price CAGR and ROE there is no directly equivalent
        # Ratio Engine CAGR calculation in src/analytics/cagr.py.
        if computed_value is None:
            comparison_rows.append(
                {
                    **row.to_dict(),
                    "computed_cagr_pct": None,
                    "absolute_difference_pct": None,
                    "divergence_pct": None,
                    "manual_review": False,
                    "validation_status": "Not comparable",
                }
            )
            continue

        absolute_difference = abs(parsed_value - computed_value)

        # Divergence expressed relative to the computed CAGR.
        if computed_value == 0:
            divergence = 0.0 if absolute_difference == 0 else float("inf")
        else:
            divergence = (absolute_difference / abs(computed_value)) * 100.0

        manual_review = divergence > 5.0

        comparison_rows.append(
            {
                **row.to_dict(),
                "computed_cagr_pct": computed_value,
                "absolute_difference_pct": absolute_difference,
                "divergence_pct": divergence,
                "manual_review": manual_review,
                "validation_status": (
                    "Divergence > 5%" if manual_review else "Validated"
                ),
            }
        )

    return pd.DataFrame(comparison_rows)


def save_outputs(
    parsed: pd.DataFrame,
    failures: pd.DataFrame,
    validation: pd.DataFrame,
) -> None:
    """Save Day 29 parser outputs."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Required structured output.
    parsed[
        [
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ]
    ].to_csv(
        PARSED_PATH,
        index=False,
    )

    # Required parse failures.
    failures.to_csv(
        FAILURES_PATH,
        index=False,
    )

    # Add a validation report beside the required outputs.
    validation_path = OUTPUT_DIR / "analysis_cagr_validation.csv"

    validation.to_csv(
        validation_path,
        index=False,
    )


def main() -> None:
    """Run the complete Day 29 parser workflow."""

    parsed, failures = parse_analysis()

    validation = cross_validate(parsed)

    save_outputs(
        parsed,
        failures,
        validation,
    )

    print("Day 29 NLP Parser")
    print("=" * 60)
    print(f"Source: {ANALYSIS_PATH}")
    print(f"Parsed rows: {len(parsed)}")
    print(f"Parse failures: {len(failures)}")

    if not validation.empty:
        comparable = validation[validation["validation_status"] != "Not comparable"]

        review = validation[validation["manual_review"] == True]

        print(f"Comparable CAGR rows: {len(comparable)}")
        print(f"Rows needing manual review (>5%): {len(review)}")

    print(f"\nSaved: {PARSED_PATH}")
    print(f"Saved: {FAILURES_PATH}")
    print(f"Saved: {OUTPUT_DIR / 'analysis_cagr_validation.csv'}")


if __name__ == "__main__":
    main()
