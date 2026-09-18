import math
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy.stats import zscore

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports"

CLUSTER_FILE = OUTPUT_DIR / "cluster_labels.csv"

PROFILE_FILE = OUTPUT_DIR / "cluster_profile.csv"
OUTLIER_FILE = OUTPUT_DIR / "outlier_report.csv"
PORTFOLIO_STATS_FILE = OUTPUT_DIR / "portfolio_stats.csv"
HEATMAP_FILE = REPORTS_DIR / "correlation_heatmap.png"


# ---------------------------------------------------------
# KPI DEFINITIONS
# ---------------------------------------------------------

KPI_COLUMNS = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

CORRELATION_KPIS = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "interest_coverage",
    "free_cash_flow_cr",
    "cash_from_operations_cr",
    "capital_expenditure_intensity_pct",
]


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------


def safe_float(value):
    """Return a finite float or None."""
    try:
        if value is None or pd.isna(value):
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def calculate_cagr(start_value, end_value, years):
    """Calculate CAGR percentage for positive starting values."""
    start_value = safe_float(start_value)
    end_value = safe_float(end_value)
    years = safe_float(years)

    if (
        start_value is None
        or end_value is None
        or years is None
        or years <= 0
        or start_value <= 0
        or end_value < 0
    ):
        return None

    try:
        result = ((end_value / start_value) ** (1.0 / years) - 1.0) * 100.0

        if not math.isfinite(result):
            return None

        return result

    except (ValueError, ZeroDivisionError):
        return None


# ---------------------------------------------------------
# LOAD DATABASE
# ---------------------------------------------------------


def load_database_data():
    """Load the financial, P&L, sector, and cluster datasets."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    if not CLUSTER_FILE.exists():
        raise FileNotFoundError(f"Missing cluster file: {CLUSTER_FILE}")

    conn = sqlite3.connect(DB_PATH)

    try:
        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            ORDER BY company_id, year
            """,
            conn,
        )

        pnl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales
            FROM profitandloss
            ORDER BY company_id, year
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

    finally:
        conn.close()

    clusters = pd.read_csv(CLUSTER_FILE)

    return (
        ratios,
        pnl,
        sectors,
        clusters,
    )


# ---------------------------------------------------------
# FEATURE BUILDING
# ---------------------------------------------------------


def latest_5yr_cagr(group, value_column):
    """Calculate a company's five-year CAGR from the latest available series."""
    if group.empty:
        return None

    temp = group.copy()

    temp["year"] = pd.to_numeric(
        temp["year"],
        errors="coerce",
    )

    temp[value_column] = pd.to_numeric(
        temp[value_column],
        errors="coerce",
    )

    temp = temp.dropna(subset=["year", value_column])

    if temp.empty:
        return None

    temp = temp.sort_values("year")

    latest_year = int(temp["year"].iloc[-1])

    target_year = latest_year - 5

    earlier = temp[temp["year"] == target_year]

    if earlier.empty:
        return None

    return calculate_cagr(
        earlier[value_column].iloc[-1],
        temp[value_column].iloc[-1],
        5,
    )


def build_latest_dataset(
    ratios,
    pnl,
    sectors,
    clusters,
):
    """Build one latest-year analytical row per company."""
    ratios = ratios.copy()
    pnl = pnl.copy()

    ratios["year"] = pd.to_numeric(
        ratios["year"],
        errors="coerce",
    )

    pnl["year"] = pd.to_numeric(
        pnl["year"],
        errors="coerce",
    )

    ratios = ratios.dropna(subset=["year"])

    pnl = pnl.dropna(subset=["year"])

    latest_ratios = (
        ratios.sort_values(["company_id", "year"])
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    rows = []

    for company_id in sorted(ratios["company_id"].dropna().astype(str).unique()):
        ratio_group = ratios[ratios["company_id"].astype(str) == company_id]

        pnl_group = pnl[pnl["company_id"].astype(str) == company_id]

        latest_rows = latest_ratios[
            latest_ratios["company_id"].astype(str) == company_id
        ]

        if latest_rows.empty:
            continue

        latest = latest_rows.iloc[-1]

        rows.append(
            {
                "company_id": company_id,
                "year": safe_float(latest.get("year")),
                "return_on_equity_pct": safe_float(latest.get("return_on_equity_pct")),
                "debt_to_equity": safe_float(latest.get("debt_to_equity")),
                "revenue_cagr_5yr": latest_5yr_cagr(
                    pnl_group,
                    "sales",
                ),
                "fcf_cagr_5yr": latest_5yr_cagr(
                    ratio_group,
                    "free_cash_flow_cr",
                ),
                "operating_profit_margin_pct": safe_float(
                    latest.get("operating_profit_margin_pct")
                ),
                "net_profit_margin_pct": safe_float(
                    latest.get("net_profit_margin_pct")
                ),
                "interest_coverage": safe_float(latest.get("interest_coverage")),
                "free_cash_flow_cr": safe_float(latest.get("free_cash_flow_cr")),
                "cash_from_operations_cr": safe_float(
                    latest.get("cash_from_operations_cr")
                ),
                "capital_expenditure_intensity_pct": safe_float(
                    latest.get("capital_expenditure_intensity_pct")
                ),
            }
        )

    result = pd.DataFrame(rows)

    # Sector information.
    sector_info = sectors.drop_duplicates("company_id")[
        [
            "company_id",
            "broad_sector",
            "sub_sector",
        ]
    ]

    result["company_id"] = result["company_id"].astype(str)

    sector_info["company_id"] = sector_info["company_id"].astype(str)

    result = result.merge(
        sector_info,
        on="company_id",
        how="left",
    )

    # Cluster information.
    clusters = clusters.copy()

    clusters["company_id"] = clusters["company_id"].astype(str)

    result = result.merge(
        clusters,
        on="company_id",
        how="left",
    )

    return result


# ---------------------------------------------------------
# CLUSTER PROFILE
# ---------------------------------------------------------


def build_cluster_profile(df):
    """Calculate mean and median for each clustering feature by cluster."""
    mean_df = (
        df.groupby(
            [
                "cluster_id",
                "cluster_name",
            ]
        )[KPI_COLUMNS]
        .mean()
        .add_suffix("_mean")
    )

    median_df = (
        df.groupby(
            [
                "cluster_id",
                "cluster_name",
            ]
        )[KPI_COLUMNS]
        .median()
        .add_suffix("_median")
    )

    counts = (
        df.groupby(
            [
                "cluster_id",
                "cluster_name",
            ]
        )
        .size()
        .rename("company_count")
    )

    profile = pd.concat(
        [
            counts,
            mean_df,
            median_df,
        ],
        axis=1,
    ).reset_index()

    return profile


# ---------------------------------------------------------
# OUTLIERS
# ---------------------------------------------------------


def build_outlier_report(df):
    """Flag companies with absolute within-sector Z-score greater than 3."""
    records = []

    for sector, group in df.groupby(
        "broad_sector",
        dropna=False,
    ):
        group = group.copy()

        for metric in KPI_COLUMNS:
            values = pd.to_numeric(
                group[metric],
                errors="coerce",
            )

            valid = values.notna()

            if valid.sum() < 2:
                continue

            z_values = pd.Series(
                float("nan"),
                index=group.index,
            )

            z_values.loc[valid] = zscore(
                values.loc[valid],
                ddof=0,
            )

            flagged = z_values.abs() > 3

            for idx in group.index[flagged.fillna(False)]:
                row = group.loc[idx]

                records.append(
                    {
                        "company_id": row["company_id"],
                        "broad_sector": sector,
                        "field": metric,
                        "value": safe_float(row[metric]),
                        "z_score": safe_float(z_values.loc[idx]),
                        "severity": "HIGH",
                        "issue": ("Absolute within-sector " "Z-score > 3"),
                        "cluster_id": row["cluster_id"],
                        "cluster_name": row["cluster_name"],
                    }
                )

    columns = [
        "company_id",
        "broad_sector",
        "field",
        "value",
        "z_score",
        "severity",
        "issue",
        "cluster_id",
        "cluster_name",
    ]

    if not records:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(
        records,
        columns=columns,
    ).sort_values(
        [
            "broad_sector",
            "field",
            "company_id",
        ]
    )


# ---------------------------------------------------------
# PORTFOLIO STATS
# ---------------------------------------------------------


def build_portfolio_stats(df):
    """Calculate P10/P25/P50/P75/P90/Mean/Std for clustering KPIs."""
    rows = []

    for metric in KPI_COLUMNS:
        series = pd.to_numeric(
            df[metric],
            errors="coerce",
        ).dropna()

        if series.empty:
            rows.append(
                {
                    "kpi": metric,
                    "P10": None,
                    "P25": None,
                    "P50": None,
                    "P75": None,
                    "P90": None,
                    "Mean": None,
                    "Std": None,
                }
            )

            continue

        rows.append(
            {
                "kpi": metric,
                "P10": series.quantile(0.10),
                "P25": series.quantile(0.25),
                "P50": series.quantile(0.50),
                "P75": series.quantile(0.75),
                "P90": series.quantile(0.90),
                "Mean": series.mean(),
                "Std": series.std(ddof=1),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# CORRELATION MATRIX
# ---------------------------------------------------------


def build_correlation_heatmap(df):
    """Create Pearson correlation heatmap for the ten requested KPIs."""
    available = [col for col in CORRELATION_KPIS if col in df.columns]

    corr = (
        df[available]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .corr(method="pearson")
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    display_names = {
        "return_on_equity_pct": "ROE",
        "debt_to_equity": "D/E",
        "revenue_cagr_5yr": "Revenue CAGR",
        "fcf_cagr_5yr": "FCF CAGR",
        "operating_profit_margin_pct": "OPM",
        "net_profit_margin_pct": "Net Margin",
        "interest_coverage": "Interest Coverage",
        "free_cash_flow_cr": "Free Cash Flow",
        "cash_from_operations_cr": "CFO",
        "capital_expenditure_intensity_pct": "CapEx Intensity",
    }

    corr_plot = corr.rename(
        index=display_names,
        columns=display_names,
    )

    plt.figure(figsize=(11, 9))

    sns.heatmap(
        corr_plot,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
    )

    plt.title("Pearson Correlation Matrix — Nifty 100 KPIs")

    plt.tight_layout()

    plt.savefig(
        HEATMAP_FILE,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close()

    return corr


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------


def main():
    """Run Sprint 6 Day 37 cluster profiling and statistics."""
    print("=== DAY 37 — CLUSTER PROFILING & STATISTICS ===")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        ratios,
        pnl,
        sectors,
        clusters,
    ) = load_database_data()

    print(f"Financial ratio rows: {len(ratios)}")

    print(f"P&L rows: {len(pnl)}")

    print(f"Cluster rows: {len(clusters)}")

    if clusters["company_id"].nunique() != 92:
        raise ValueError(
            "cluster_labels.csv must contain "
            f"92 companies, found "
            f"{clusters['company_id'].nunique()}."
        )

    df = build_latest_dataset(
        ratios,
        pnl,
        sectors,
        clusters,
    )

    print(f"Latest analytical rows: {len(df)}")

    if df["company_id"].nunique() != 92:
        raise ValueError("Expected 92 latest company rows.")

    # -----------------------------------------------------
    # Cluster profile
    # -----------------------------------------------------

    profile = build_cluster_profile(df)

    profile.to_csv(
        PROFILE_FILE,
        index=False,
    )

    print(f"\nCluster profile saved: {PROFILE_FILE}")

    print("\nCluster profile:")

    print(profile.to_string(index=False))

    # -----------------------------------------------------
    # Outliers
    # -----------------------------------------------------

    outliers = build_outlier_report(df)

    outliers.to_csv(
        OUTLIER_FILE,
        index=False,
    )

    print(f"\nOutlier report saved: {OUTLIER_FILE}")

    print(f"Outlier rows: {len(outliers)}")

    # -----------------------------------------------------
    # Portfolio statistics
    # -----------------------------------------------------

    stats = build_portfolio_stats(df)

    stats.to_csv(
        PORTFOLIO_STATS_FILE,
        index=False,
    )

    print(f"\nPortfolio stats saved: " f"{PORTFOLIO_STATS_FILE}")

    print(stats.to_string(index=False))

    # -----------------------------------------------------
    # Correlation heatmap
    # -----------------------------------------------------

    corr = build_correlation_heatmap(df)

    print(f"\nCorrelation heatmap saved: " f"{HEATMAP_FILE}")

    print("\nCorrelation matrix:")

    print(corr.round(3).to_string())

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    print("\n=== DAY 37 VALIDATION ===")

    print(
        "Companies:",
        df["company_id"].nunique(),
    )

    print(
        "Clusters:",
        sorted(df["cluster_id"].dropna().astype(int).unique().tolist()),
    )

    print(
        "Cluster names:",
        sorted(df["cluster_name"].dropna().unique().tolist()),
    )

    print(
        "Outlier rows:",
        len(outliers),
    )

    print(
        "Portfolio-stat rows:",
        len(stats),
    )

    print(
        "Correlation KPI count:",
        len(corr.columns),
    )

    if df["company_id"].nunique() != 92:
        raise ValueError("Company coverage validation failed.")

    if set(df["cluster_id"].dropna().astype(int).unique()) != set(range(5)):
        raise ValueError("Expected cluster IDs 0-4.")

    if len(stats) != len(KPI_COLUMNS):
        raise ValueError("Portfolio statistics are incomplete.")

    if len(corr.columns) != 10:
        raise ValueError("Correlation matrix should contain 10 KPIs.")

    print("\nDay 37 completed successfully.")


if __name__ == "__main__":
    main()
