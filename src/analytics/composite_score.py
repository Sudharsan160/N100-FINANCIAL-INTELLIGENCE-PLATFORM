"""
Day 17 - Composite Quality Score
N100 Financial Intelligence Platform

Composite Score = 0 to 100

Profitability: 35
    ROE  = 15
    ROCE = 10
    NPM  = 10

Cash Quality: 30
    FCF CAGR       = 15
    CFO/PAT ratio  = 10
    FCF positive   = 5

Growth: 20
    Revenue CAGR 5Y = 10
    PAT CAGR 5Y     = 10

Leverage: 15
    D/E score = 10
    ICR score = 5

Normalization:
    1. Winsorise each metric at P10/P90.
    2. Normalize within broad_sector.
    3. Lower D/E is better.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


DB_PATH = "nifty100.db"
OUTPUT_PATH = Path("output/composite_scores.csv")


# ============================================================
# HELPERS
# ============================================================

def calculate_cagr(start_value, end_value, years=5):
    """Calculate CAGR when both values are positive."""
    if pd.isna(start_value) or pd.isna(end_value):
        return np.nan

    if start_value <= 0 or end_value <= 0:
        return np.nan

    return ((end_value / start_value) ** (1 / years) - 1) * 100


def winsorize(series: pd.Series) -> pd.Series:
    """
    Cap metric values at P10 and P90.
    Infinite values are treated as missing for percentile calculation.
    """
    result = pd.to_numeric(series, errors="coerce").copy()

    finite_values = result.replace([np.inf, -np.inf], np.nan).dropna()

    if finite_values.empty:
        return result

    p10 = finite_values.quantile(0.10)
    p90 = finite_values.quantile(0.90)

    result = result.replace(np.inf, p90)
    result = result.replace(-np.inf, p10)

    return result.clip(lower=p10, upper=p90)


def sector_normalize(
    df: pd.DataFrame,
    column: str,
    higher_is_better: bool = True,
) -> pd.Series:
    """
    Normalize a metric to 0-100 within each broad_sector.
    """

    def normalize_group(series: pd.Series) -> pd.Series:
        minimum = series.min()
        maximum = series.max()

        if pd.isna(minimum) or pd.isna(maximum):
            return pd.Series(np.nan, index=series.index)

        if minimum == maximum:
            return pd.Series(50.0, index=series.index)

        score = ((series - minimum) / (maximum - minimum)) * 100

        if not higher_is_better:
            score = 100 - score

        return score

    return df.groupby(
        "broad_sector",
        dropna=False,
        group_keys=False,
    )[column].transform(normalize_group)


# ============================================================
# LOAD DATABASE
# ============================================================

def load_data(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)

    ratios = pd.read_sql_query(
        """
        SELECT
            id,
            company_id,
            year,
            return_on_equity_pct,
            roce_pct,
            net_profit_margin_pct,
            free_cash_flow_cr,
            cash_from_operations_cr,
            cash_flow_to_net_profit,
            debt_to_equity,
            interest_coverage
        FROM financial_ratios
        ORDER BY company_id, year, id
        """,
        conn,
    )

    pnl = pd.read_sql_query(
        """
        SELECT
            id,
            company_id,
            year,
            sales,
            net_profit
        FROM profitandloss
        ORDER BY company_id, year, id
        """,
        conn,
    )

    sectors = pd.read_sql_query(
        """
        SELECT
            company_id,
            broad_sector,
            sub_sector
        FROM sectors
        """,
        conn,
    )

    conn.close()

    ratios["year"] = pd.to_numeric(ratios["year"], errors="coerce")
    pnl["year"] = pd.to_numeric(pnl["year"], errors="coerce")

    # Keep one row per company/year.
    ratios = ratios.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    pnl = pnl.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    # Latest available ratio year for every company.
    latest_ratios = (
        ratios
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest_ratios = latest_ratios.merge(
        sectors[
            ["company_id", "broad_sector", "sub_sector"]
        ].drop_duplicates("company_id"),
        on="company_id",
        how="left",
    )

    return latest_ratios.reset_index(drop=True), ratios, pnl


# ============================================================
# HISTORICAL CAGR METRICS
# ============================================================

def add_growth_metrics(
    df: pd.DataFrame,
    ratios: pd.DataFrame,
    pnl: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate 5-year Revenue CAGR, PAT CAGR and FCF CAGR."""

    result = df.copy()

    # --------------------------------------------------------
    # Revenue CAGR 5Y + PAT CAGR 5Y
    # --------------------------------------------------------

    current_pnl = pnl.rename(
        columns={
            "sales": "sales_current",
            "net_profit": "net_profit_current",
        }
    )[
        [
            "company_id",
            "year",
            "sales_current",
            "net_profit_current",
        ]
    ]

    result = result.merge(
        current_pnl,
        on=["company_id", "year"],
        how="left",
    )

    historical_pnl = pnl.rename(
        columns={
            "year": "historical_year",
            "sales": "sales_5y",
            "net_profit": "net_profit_5y",
        }
    )[
        [
            "company_id",
            "historical_year",
            "sales_5y",
            "net_profit_5y",
        ]
    ]

    result["historical_year"] = result["year"] - 5

    result = result.merge(
        historical_pnl,
        on=["company_id", "historical_year"],
        how="left",
    )

    result["revenue_cagr_5yr_pct"] = result.apply(
        lambda row: calculate_cagr(
            row["sales_5y"],
            row["sales_current"],
            5,
        ),
        axis=1,
    )

    result["pat_cagr_5yr_pct"] = result.apply(
        lambda row: calculate_cagr(
            row["net_profit_5y"],
            row["net_profit_current"],
            5,
        ),
        axis=1,
    )

    # --------------------------------------------------------
    # FCF CAGR 5Y
    # --------------------------------------------------------

    current_fcf = ratios.rename(
        columns={"free_cash_flow_cr": "fcf_current"}
    )[
        [
            "company_id",
            "year",
            "fcf_current",
        ]
    ]

    result = result.merge(
        current_fcf,
        on=["company_id", "year"],
        how="left",
    )

    historical_fcf = ratios.rename(
        columns={
            "year": "historical_fcf_year",
            "free_cash_flow_cr": "fcf_5y",
        }
    )[
        [
            "company_id",
            "historical_fcf_year",
            "fcf_5y",
        ]
    ]

    result["historical_fcf_year"] = result["year"] - 5

    result = result.merge(
        historical_fcf,
        on=["company_id", "historical_fcf_year"],
        how="left",
    )

    result["fcf_cagr_5yr_pct"] = result.apply(
        lambda row: calculate_cagr(
            row["fcf_5y"],
            row["fcf_current"],
            5,
        ),
        axis=1,
    )

    return result


# ============================================================
# COMPOSITE SCORE
# ============================================================

def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the complete 0-100 composite score."""

    result = df.copy()

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    metrics = {
        "return_on_equity_pct": True,
        "roce_pct": True,
        "net_profit_margin_pct": True,
        "fcf_cagr_5yr_pct": True,
        "cash_flow_to_net_profit": True,
        "revenue_cagr_5yr_pct": True,
        "pat_cagr_5yr_pct": True,
        "debt_to_equity": False,
        "interest_coverage": True,
    }

    # --------------------------------------------------------
    # P10/P90 winsorisation
    # --------------------------------------------------------

    for metric in metrics:
        result[f"{metric}_winsorized"] = winsorize(
            result[metric]
        )

    # --------------------------------------------------------
    # Sector-relative 0-100 scores
    # --------------------------------------------------------

    for metric, higher_is_better in metrics.items():
        result[f"{metric}_normalized"] = sector_normalize(
            result,
            f"{metric}_winsorized",
            higher_is_better=higher_is_better,
        )

    # Missing normalized values become 0.
    # This avoids inventing values when source data is unavailable.
    normalized_columns = [
        f"{metric}_normalized"
        for metric in metrics
    ]

    result[normalized_columns] = (
        result[normalized_columns].fillna(0)
    )

    # --------------------------------------------------------
    # FCF positive flag = 5 points
    # --------------------------------------------------------

    result["fcf_positive_score"] = np.where(
        result["free_cash_flow_cr"] > 0,
        5.0,
        0.0,
    )

    # --------------------------------------------------------
    # PROFITABILITY = 35
    # --------------------------------------------------------

    result["profitability_score"] = (
        result["return_on_equity_pct_normalized"] * 0.15
        + result["roce_pct_normalized"] * 0.10
        + result["net_profit_margin_pct_normalized"] * 0.10
    )

    # --------------------------------------------------------
    # CASH QUALITY = 30
    # --------------------------------------------------------

    result["cash_quality_score"] = (
        result["fcf_cagr_5yr_pct_normalized"] * 0.15
        + result["cash_flow_to_net_profit_normalized"] * 0.10
        + result["fcf_positive_score"]
    )

    # --------------------------------------------------------
    # GROWTH = 20
    # --------------------------------------------------------

    result["growth_score"] = (
        result["revenue_cagr_5yr_pct_normalized"] * 0.10
        + result["pat_cagr_5yr_pct_normalized"] * 0.10
    )

    # --------------------------------------------------------
    # LEVERAGE = 15
    # --------------------------------------------------------

    result["leverage_score"] = (
        result["debt_to_equity_normalized"] * 0.10
        + result["interest_coverage_normalized"] * 0.05
    )

    # --------------------------------------------------------
    # FINAL SCORE = 100
    # --------------------------------------------------------

    result["composite_quality_score"] = (
        result["profitability_score"]
        + result["cash_quality_score"]
        + result["growth_score"]
        + result["leverage_score"]
    ).clip(0, 100).round(2)

    return result


# ============================================================
# EXPORT
# ============================================================

def export_scores(
    df: pd.DataFrame,
    output_path: Path = OUTPUT_PATH,
):
    """Export the composite scores to CSV."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    columns = [
        "company_id",
        "year",
        "broad_sector",
        "sub_sector",
        "return_on_equity_pct",
        "roce_pct",
        "net_profit_margin_pct",
        "free_cash_flow_cr",
        "fcf_cagr_5yr_pct",
        "cash_flow_to_net_profit",
        "revenue_cagr_5yr_pct",
        "pat_cagr_5yr_pct",
        "debt_to_equity",
        "interest_coverage",
        "profitability_score",
        "cash_quality_score",
        "growth_score",
        "leverage_score",
        "composite_quality_score",
    ]

    export_df = (
        df[columns]
        .sort_values(
            "composite_quality_score",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    export_df.to_csv(
        output_path,
        index=False,
    )

    return export_df


# ============================================================
# MAIN
# ============================================================

def main():
    print("Loading N100 financial data...")

    latest, ratios, pnl = load_data(DB_PATH)

    print(f"Latest company rows: {len(latest)}")
    print(f"Ratio history rows: {len(ratios)}")
    print(f"P&L history rows: {len(pnl)}")

    print("Calculating 5-year growth metrics...")

    latest = add_growth_metrics(
        latest,
        ratios,
        pnl,
    )

    print("Calculating sector-relative composite scores...")

    scored = calculate_scores(latest)

    exported = export_scores(scored)

    print(
        f"Composite score rows exported: {len(exported)}"
    )

    print("\nTop 10 companies:")
    print(
        exported[
            [
                "company_id",
                "broad_sector",
                "composite_quality_score",
            ]
        ].head(10).to_string(index=False)
    )

    print(
        f"\nExport created: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()