import math
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports"

CLUSTER_FILE = OUTPUT_DIR / "cluster_labels.csv"
ELBOW_FILE = REPORTS_DIR / "elbow_plot.png"


FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


# =========================================================
# HELPERS
# =========================================================


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
    """Calculate CAGR percentage when the input values support it."""
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


# =========================================================
# DATABASE
# =========================================================


def load_data():
    """Load financial ratios, P&L, cash flow, and sector information."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

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

    return ratios, pnl, sectors


# =========================================================
# CAGR FEATURE CALCULATION
# =========================================================


def calculate_latest_5yr_cagr(series_df, value_column):
    """
    Calculate the latest available 5-year CAGR for a company.

    The function uses the latest observation and the observation
    five years earlier. If either value cannot support CAGR,
    None is returned.
    """
    if series_df.empty:
        return None

    temp = series_df.copy()

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

    start_value = earlier[value_column].iloc[-1]

    end_value = temp[value_column].iloc[-1]

    return calculate_cagr(
        start_value,
        end_value,
        5,
    )


def build_feature_dataset(
    ratios,
    pnl,
    sectors,
):
    """Build one latest clustering row for every company."""
    ratio_latest = ratios.copy()

    ratio_latest["year"] = pd.to_numeric(
        ratio_latest["year"],
        errors="coerce",
    )

    ratio_latest = ratio_latest.dropna(subset=["year"])

    ratio_latest = (
        ratio_latest.sort_values(["company_id", "year"])
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    rows = []

    for company_id in sorted(ratios["company_id"].dropna().astype(str).unique()):
        ratio_group = ratios[ratios["company_id"].astype(str) == company_id].copy()

        pnl_group = pnl[pnl["company_id"].astype(str) == company_id].copy()

        latest_rows = ratio_latest[ratio_latest["company_id"].astype(str) == company_id]

        if latest_rows.empty:
            continue

        latest = latest_rows.iloc[-1]

        revenue_cagr = calculate_latest_5yr_cagr(
            pnl_group,
            "sales",
        )

        fcf_cagr = calculate_latest_5yr_cagr(
            ratio_group,
            "free_cash_flow_cr",
        )

        rows.append(
            {
                "company_id": company_id,
                "year": safe_float(latest.get("year")),
                "return_on_equity_pct": safe_float(latest.get("return_on_equity_pct")),
                "debt_to_equity": safe_float(latest.get("debt_to_equity")),
                "revenue_cagr_5yr": revenue_cagr,
                "fcf_cagr_5yr": fcf_cagr,
                "operating_profit_margin_pct": safe_float(
                    latest.get("operating_profit_margin_pct")
                ),
            }
        )

    features = pd.DataFrame(rows)

    sector_info = sectors.drop_duplicates("company_id")[
        [
            "company_id",
            "broad_sector",
            "sub_sector",
        ]
    ]

    features["company_id"] = features["company_id"].astype(str)

    sector_info["company_id"] = sector_info["company_id"].astype(str)

    features = features.merge(
        sector_info,
        on="company_id",
        how="left",
    )

    return features


# =========================================================
# SECTOR MEDIAN IMPUTATION
# =========================================================


def sector_median_impute(
    df,
    features,
):
    """Impute missing clustering values using sector medians."""
    result = df.copy()

    for feature in features:
        result[feature] = pd.to_numeric(
            result[feature],
            errors="coerce",
        )

        sector_medians = result.groupby("broad_sector")[feature].transform("median")

        result[feature] = result[feature].fillna(sector_medians)

        overall_median = result[feature].median()

        if pd.notna(overall_median):
            result[feature] = result[feature].fillna(overall_median)

    return result


# =========================================================
# ELBOW
# =========================================================


def build_elbow_plot(X_scaled):
    """Generate the KMeans elbow plot for k=2 through k=10."""
    inertias = []
    ks = list(range(2, 11))

    for k in ks:
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10,
        )

        model.fit(X_scaled)

        inertias.append(model.inertia_)

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(figsize=(8, 5))

    plt.plot(
        ks,
        inertias,
        marker="o",
    )

    plt.axvline(
        5,
        linestyle="--",
        alpha=0.5,
    )

    plt.xlabel("Number of clusters (k)")

    plt.ylabel("Inertia")

    plt.title("KMeans Elbow Curve")

    plt.xticks(ks)

    plt.grid(
        True,
        alpha=0.25,
    )

    plt.tight_layout()

    plt.savefig(
        ELBOW_FILE,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close()

    return pd.DataFrame(
        {
            "k": ks,
            "inertia": inertias,
        }
    )


# =========================================================
# CLUSTER NAMING
# =========================================================


def choose_cluster_names(
    cluster_profile,
):
    """
    Assign descriptive names based on cluster-level
    financial characteristics.
    """
    names = {}

    remaining = list(cluster_profile.index)

    # Highest-quality profile.
    quality_score = (
        cluster_profile["return_on_equity_pct"].rank(pct=True)
        + cluster_profile["operating_profit_margin_pct"].rank(pct=True)
        + cluster_profile["revenue_cagr_5yr"].rank(pct=True)
        - cluster_profile["debt_to_equity"].rank(pct=True)
    )

    high_quality_id = quality_score.idxmax()

    names[int(high_quality_id)] = "High-Quality Compounders"

    remaining.remove(high_quality_id)

    # Highest growth cluster.
    if remaining:
        growth_score = (
            cluster_profile.loc[
                remaining,
                "revenue_cagr_5yr",
            ]
            + cluster_profile.loc[
                remaining,
                "fcf_cagr_5yr",
            ]
        )

        growth_id = growth_score.idxmax()

        names[int(growth_id)] = "Emerging Growth"

        remaining.remove(growth_id)

    # Lowest ROE / OPM / growth relative profile.
    if remaining:
        distress_score = (
            cluster_profile.loc[
                remaining,
                "return_on_equity_pct",
            ].rank(pct=True)
            + cluster_profile.loc[
                remaining,
                "operating_profit_margin_pct",
            ].rank(pct=True)
            + cluster_profile.loc[
                remaining,
                "revenue_cagr_5yr",
            ].rank(pct=True)
            - cluster_profile.loc[
                remaining,
                "debt_to_equity",
            ].rank(pct=True)
        )

        distressed_id = distress_score.idxmin()

        names[int(distressed_id)] = "Turnaround / Cyclical"

        remaining.remove(distressed_id)

    # Low-debt defensive cluster.
    if remaining:
        defensive_score = (
            -cluster_profile.loc[
                remaining,
                "debt_to_equity",
            ]
            + cluster_profile.loc[
                remaining,
                "operating_profit_margin_pct",
            ]
        )

        defensive_id = defensive_score.idxmax()

        names[int(defensive_id)] = "Defensive Quality"

        remaining.remove(defensive_id)

    # Final cluster.
    for cluster_id in remaining:
        names[int(cluster_id)] = "Value / Balanced"

    return names


# =========================================================
# DISTANCES
# =========================================================


def calculate_cluster_distances(
    X_scaled,
    model,
):
    """Calculate Euclidean distance from each company to its centroid."""
    distances = []

    for row, label in zip(
        X_scaled,
        model.labels_,
    ):
        centroid = model.cluster_centers_[label]

        distance = float(((row - centroid) ** 2).sum() ** 0.5)

        distances.append(distance)

    return distances


# =========================================================
# MAIN
# =========================================================


def main():
    """Run Sprint 6 Day 36 KMeans clustering."""
    print("=== DAY 36 — KMEANS CLUSTERING ===")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ratios, pnl, sectors = load_data()

    print(f"Financial ratio rows: {len(ratios)}")

    print(f"P&L rows: {len(pnl)}")

    features = build_feature_dataset(
        ratios,
        pnl,
        sectors,
    )

    print(f"Companies with latest rows: " f"{features['company_id'].nunique()}")

    if features["company_id"].nunique() != 92:
        raise ValueError(
            "Expected 92 companies, " f"found {features['company_id'].nunique()}."
        )

    # -----------------------------------------------------
    # Sector median imputation
    # -----------------------------------------------------

    features = sector_median_impute(
        features,
        FEATURES,
    )

    missing_after_imputation = features[FEATURES].isna().sum()

    missing_after_imputation = missing_after_imputation[missing_after_imputation > 0]

    if not missing_after_imputation.empty:
        raise ValueError(
            "Missing values remain after "
            "sector-median imputation:\n"
            f"{missing_after_imputation}"
        )

    # -----------------------------------------------------
    # StandardScaler
    # -----------------------------------------------------

    X = features[FEATURES].astype(float)

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    scaled_df = pd.DataFrame(
        X_scaled,
        columns=FEATURES,
    )

    print("\nScaled means:")

    print(scaled_df.mean().round(6).to_dict())

    print("Scaled std:")

    print(scaled_df.std(ddof=0).round(6).to_dict())

    # -----------------------------------------------------
    # Elbow
    # -----------------------------------------------------

    elbow = build_elbow_plot(X_scaled)

    print("\nElbow values:")

    print(elbow.to_string(index=False))

    print(f"\nElbow plot saved: {ELBOW_FILE}")

    # -----------------------------------------------------
    # KMeans 5 clusters
    # -----------------------------------------------------

    model = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=10,
    )

    labels = model.fit_predict(X_scaled)

    distances = calculate_cluster_distances(
        X_scaled,
        model,
    )

    features["cluster_id"] = labels

    features["distance_from_centroid"] = distances

    # -----------------------------------------------------
    # Cluster profiles
    # -----------------------------------------------------

    cluster_profile = features.groupby("cluster_id")[FEATURES].mean()

    cluster_names = choose_cluster_names(cluster_profile)

    features["cluster_name"] = features["cluster_id"].map(cluster_names)

    # -----------------------------------------------------
    # Output
    # -----------------------------------------------------

    output = features[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    output = output.sort_values("company_id")

    output.to_csv(
        CLUSTER_FILE,
        index=False,
    )

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    print("\n=== CLUSTER VALIDATION ===")

    print(
        "Companies clustered:",
        output["company_id"].nunique(),
    )

    print(
        "Cluster IDs:",
        sorted(output["cluster_id"].unique().tolist()),
    )

    print("\nCluster distribution:")

    distribution = (
        output.groupby(
            [
                "cluster_id",
                "cluster_name",
            ]
        )
        .size()
        .sort_index()
    )

    print(distribution.to_string())

    missing_assignments = (
        output[
            [
                "cluster_id",
                "cluster_name",
                "distance_from_centroid",
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    invalid_ids = output[~output["cluster_id"].between(0, 4)]

    invalid_distances = output[output["distance_from_centroid"] < 0]

    print(
        "\nMissing assignments:",
        missing_assignments,
    )

    print(
        "Invalid cluster IDs:",
        len(invalid_ids),
    )

    print(
        "Negative distances:",
        len(invalid_distances),
    )

    if output["company_id"].nunique() != 92:
        raise ValueError("Output does not contain 92 companies.")

    if set(output["cluster_id"]) != set(range(5)):
        raise ValueError("Expected cluster IDs 0-4.")

    if missing_assignments != 0 or len(invalid_ids) != 0 or len(invalid_distances) != 0:
        raise ValueError("Cluster validation failed.")

    if output["cluster_name"].isna().any():
        raise ValueError("Some clusters do not have names.")

    print(f"\nCluster labels saved: {CLUSTER_FILE}")

    print("Day 36 completed successfully.")


if __name__ == "__main__":
    main()
