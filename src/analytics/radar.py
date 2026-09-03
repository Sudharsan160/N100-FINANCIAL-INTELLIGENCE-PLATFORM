from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "nifty100.db"
PEER_GROUPS_PATH = PROJECT_ROOT / "data" / "raw" / "peer_groups.xlsx"
COMPOSITE_PATH = PROJECT_ROOT / "output" / "composite_scores.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "radar_charts"


AXES = [
    "ROE",
    "ROCE",
    "NPM",
    "D/E",
    "FCF Score",
    "PAT CAGR 5yr",
    "Revenue CAGR 5yr",
    "Composite Score",
]


def calculate_cagr(
    start_value,
    end_value,
    years=5,
):
    """Calculate CAGR when both values are positive."""

    if pd.isna(start_value) or pd.isna(end_value):
        return np.nan

    if start_value <= 0 or end_value <= 0:
        return np.nan

    return (
        (end_value / start_value) ** (1 / years) - 1
    ) * 100


def calculate_history_cagr(
    history,
    value_column,
    output_column,
):
    """Calculate exact 5-year CAGR."""

    rows = []

    data = history[
        ["company_id", "year", value_column]
    ].copy()

    data["year"] = pd.to_numeric(
        data["year"],
        errors="coerce",
    )

    data[value_column] = pd.to_numeric(
        data[value_column],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "company_id",
            "year",
            value_column,
        ]
    )

    data = data.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="last",
    )

    for company_id, group in data.groupby(
        "company_id",
        sort=False,
    ):
        group = (
            group
            .sort_values("year")
            .set_index("year")
        )

        for end_year in group.index:

            start_year = end_year - 5

            if start_year not in group.index:
                continue

            start_value = group.loc[
                start_year,
                value_column,
            ]

            end_value = group.loc[
                end_year,
                value_column,
            ]

            cagr = calculate_cagr(
                start_value,
                end_value,
                5,
            )

            if pd.isna(cagr):
                continue

            rows.append(
                {
                    "company_id": company_id,
                    "year": int(end_year),
                    output_column: cagr,
                }
            )

    return pd.DataFrame(rows)


def load_data():
    """Load latest metrics, peer groups and composite scores."""

    if not PEER_GROUPS_PATH.exists():
        raise FileNotFoundError(
            f"Peer groups not found: {PEER_GROUPS_PATH}"
        )

    if not COMPOSITE_PATH.exists():
        raise FileNotFoundError(
            f"Composite scores not found: {COMPOSITE_PATH}"
        )

    peers = pd.read_excel(
        PEER_GROUPS_PATH
    )

    with sqlite3.connect(DB_PATH) as conn:

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                return_on_equity_pct,
                roce_pct,
                net_profit_margin_pct,
                debt_to_equity,
                free_cash_flow_cr,
                interest_coverage,
                asset_turnover
            FROM financial_ratios
            """,
            conn,
        )

        pnl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales,
                net_profit
            FROM profitandloss
            """,
            conn,
        )

    # --------------------------------------------------------
    # Clean years
    # --------------------------------------------------------

    ratios["year"] = pd.to_numeric(
        ratios["year"],
        errors="coerce",
    )

    pnl["year"] = pd.to_numeric(
        pnl["year"],
        errors="coerce",
    )

    ratios = ratios.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="last",
    )

    pnl = pnl.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="last",
    )

    # --------------------------------------------------------
    # Latest ratio data
    # --------------------------------------------------------

    latest = (
        ratios
        .sort_values(
            [
                "company_id",
                "year",
            ]
        )
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    # --------------------------------------------------------
    # Historical growth
    # --------------------------------------------------------

    pat_cagr = calculate_history_cagr(
        pnl,
        "net_profit",
        "pat_cagr_5yr",
    )

    revenue_cagr = calculate_history_cagr(
        pnl,
        "sales",
        "revenue_cagr_5yr",
    )

    latest = latest.merge(
        pat_cagr,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    latest = latest.merge(
        revenue_cagr,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    # --------------------------------------------------------
    # FCF positive score
    # --------------------------------------------------------

    latest["fcf_score"] = np.where(
        latest["free_cash_flow_cr"] > 0,
        100.0,
        0.0,
    )

    # --------------------------------------------------------
    # Composite score
    # --------------------------------------------------------

    composite = pd.read_csv(
        COMPOSITE_PATH
    )

    composite = composite[
        [
            "company_id",
            "composite_quality_score",
        ]
    ].drop_duplicates(
        subset=["company_id"],
        keep="last",
    )

    latest = latest.merge(
        composite,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Peer groups
    # --------------------------------------------------------

    peers = peers[
        [
            "peer_group_name",
            "company_id",
            "is_benchmark",
        ]
    ].copy()

    peers["company_id"] = (
        peers["company_id"]
        .astype(str)
        .str.strip()
    )

    latest["company_id"] = (
        latest["company_id"]
        .astype(str)
        .str.strip()
    )

    latest = latest.merge(
        peers,
        on="company_id",
        how="left",
    )

    return latest


def normalize_peer_values(
    group,
):
    """
    Normalize the 8 radar metrics from 0 to 100
    within the peer group.
    """

    result = group.copy()

    metric_map = {
        "ROE": (
            "return_on_equity_pct",
            False,
        ),
        "ROCE": (
            "roce_pct",
            False,
        ),
        "NPM": (
            "net_profit_margin_pct",
            False,
        ),
        "D/E": (
            "debt_to_equity",
            True,
        ),
        "FCF Score": (
            "fcf_score",
            False,
        ),
        "PAT CAGR 5yr": (
            "pat_cagr_5yr",
            False,
        ),
        "Revenue CAGR 5yr": (
            "revenue_cagr_5yr",
            False,
        ),
        "Composite Score": (
            "composite_quality_score",
            False,
        ),
    }

    normalized = pd.DataFrame(
        index=result.index
    )

    for axis, (
        column,
        inverse,
    ) in metric_map.items():

        values = pd.to_numeric(
            result[column],
            errors="coerce",
        )

        valid = values.dropna()

        if valid.empty:
            normalized[axis] = 50.0
            continue

        p10 = valid.quantile(0.10)
        p90 = valid.quantile(0.90)

        clipped = values.clip(
            lower=p10,
            upper=p90,
        )

        if p10 == p90:
            score = pd.Series(
                50.0,
                index=result.index,
            )
        else:
            score = (
                (clipped - p10)
                / (p90 - p10)
                * 100
            )

        if inverse:
            score = 100 - score

        normalized[axis] = (
            score.fillna(50.0)
        )

    return normalized


def create_radar_chart(
    company_id,
    peer_group_name,
    company_scores,
    peer_scores,
    output_path,
):
    """Create one company-vs-peer radar chart."""

    angles = np.linspace(
        0,
        2 * np.pi,
        len(AXES),
        endpoint=False,
    )

    company_values = (
        company_scores[AXES]
        .fillna(0)
        .tolist()
    )

    peer_values = (
        peer_scores[AXES]
        .fillna(0)
        .tolist()
    )

    company_values += company_values[:1]
    peer_values += peer_values[:1]

    plot_angles = (
        angles.tolist()
        + [angles[0]]
    )

    fig = plt.figure(
        figsize=(9, 9)
    )

    ax = fig.add_subplot(
        111,
        polar=True,
    )

    ax.set_theta_offset(
        np.pi / 2
    )

    ax.set_theta_direction(
        -1
    )

    ax.set_xticks(
        angles
    )

    ax.set_xticklabels(
        AXES,
        fontsize=10,
    )

    ax.set_ylim(
        0,
        100,
    )

    ax.set_yticks(
        [
            20,
            40,
            60,
            80,
            100,
        ]
    )

    ax.set_yticklabels(
        [
            "20",
            "40",
            "60",
            "80",
            "100",
        ],
        fontsize=8,
    )

    ax.plot(
        plot_angles,
        company_values,
        linewidth=2,
        label=company_id,
    )

    ax.fill(
        plot_angles,
        company_values,
        alpha=0.20,
    )

    ax.plot(
        plot_angles,
        peer_values,
        linestyle="--",
        linewidth=1.5,
        label="Peer Average",
    )

    ax.set_title(
        f"{company_id} — {peer_group_name}",
        fontsize=14,
        pad=25,
    )

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(
            1.25,
            1.10,
        ),
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)


def generate_all_charts():
    """Generate radar chart for every company in peer groups."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = load_data()

    generated = 0

    peer_data = data[
        data["peer_group_name"].notna()
    ].copy()

    # --------------------------------------------------------
    # Generate peer-group charts
    # --------------------------------------------------------

    for peer_group_name, group in peer_data.groupby(
        "peer_group_name",
        sort=True,
    ):

        normalized = normalize_peer_values(
            group
        )

        peer_average = normalized.mean(
            numeric_only=True
        )

        for index, company in group.iterrows():

            company_scores = normalized.loc[
                index
            ]

            output_path = (
                OUTPUT_DIR
                / f"{company['company_id']}_radar.png"
            )

            create_radar_chart(
                company_id=company["company_id"],
                peer_group_name=peer_group_name,
                company_scores=company_scores,
                peer_scores=peer_average,
                output_path=output_path,
            )

            generated += 1

    # --------------------------------------------------------
    # No-peer companies
    # --------------------------------------------------------

    no_peer = data[
        data["peer_group_name"].isna()
    ].copy()

    if not no_peer.empty:

        normalized_all = normalize_peer_values(
            data
        )

        nifty_average = normalized_all.mean(
            numeric_only=True
        )

        for index, company in no_peer.iterrows():

            company_scores = normalized_all.loc[
                index
            ]

            output_path = (
                OUTPUT_DIR
                / f"{company['company_id']}_radar.png"
            )

            create_radar_chart(
                company_id=company["company_id"],
                peer_group_name="Nifty 100 Average",
                company_scores=company_scores,
                peer_scores=nifty_average,
                output_path=output_path,
            )

            generated += 1

    print(
        f"Radar charts generated: {generated}"
    )

    print(
        f"Output directory: {OUTPUT_DIR}"
    )


def main():
    generate_all_charts()


if __name__ == "__main__":
    main()