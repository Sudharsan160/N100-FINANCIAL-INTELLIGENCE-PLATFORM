import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_peers,
    get_ratios,
    get_sectors,
)

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "nifty100.db"


st.title("Peer Comparison")
st.caption("Compare a company against its peer-group benchmark.")


# ---------------------------------------------------------
# Load base data
# ---------------------------------------------------------
companies = get_companies()
sectors = get_sectors()


# ---------------------------------------------------------
# Peer groups
# ---------------------------------------------------------
with sqlite3.connect(str(DB_PATH)) as conn:
    groups = pd.read_sql_query(
        """
        SELECT DISTINCT peer_group_name
        FROM peer_groups
        ORDER BY peer_group_name
        """,
        conn,
    )


if groups.empty:
    st.error("No peer groups are available.")
    st.stop()


group_names = groups["peer_group_name"].dropna().tolist()

selected_group = st.selectbox(
    "Select Peer Group",
    group_names,
)


# ---------------------------------------------------------
# Companies in selected peer group
# ---------------------------------------------------------
peer_df = get_peers(selected_group)

if peer_df.empty:
    st.warning("No companies found in this peer group.")
    st.stop()


peer_ids = peer_df["company_id"].astype(str).tolist()


# ---------------------------------------------------------
# Select company
# ---------------------------------------------------------
company_lookup = companies[companies["company_id"].astype(str).isin(peer_ids)].copy()

company_lookup["label"] = (
    company_lookup["company_id"].astype(str)
    + " — "
    + company_lookup["company_name"].astype(str)
)

company_labels = company_lookup["label"].tolist()

if not company_labels:
    st.warning("No company information is available for this peer group.")
    st.stop()


selected_label = st.selectbox(
    "Benchmark Company",
    company_labels,
)

selected_company = selected_label.split(" — ", 1)[0]


# ---------------------------------------------------------
# Load ratio data for peer companies
# ---------------------------------------------------------
ratio_frames = []

for company_id in peer_ids:
    df = get_ratios(company_id)

    if not df.empty:
        df = df.copy()
        df["company_id"] = company_id
        ratio_frames.append(df)


if not ratio_frames:
    st.warning("Financial ratio data is unavailable for this peer group.")
    st.stop()


ratios = pd.concat(ratio_frames, ignore_index=True)

ratios["year"] = pd.to_numeric(
    ratios["year"],
    errors="coerce",
)

ratios = (
    ratios.sort_values(["company_id", "year"])
    .groupby("company_id", as_index=False)
    .tail(1)
)


# ---------------------------------------------------------
# Peer metrics
# ---------------------------------------------------------
metric_map = {
    "ROE": "return_on_equity_pct",
    "ROCE": "roce_pct",
    "NPM": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "FCF": "free_cash_flow_cr",
    "Revenue CAGR": "revenue_growth_pct",
    "PAT CAGR": "net_profit_growth_pct",
    "EPS CAGR": "eps_growth_pct",
}


# Add missing metric columns safely.
for column in metric_map.values():
    if column not in ratios.columns:
        ratios[column] = pd.NA

for column in metric_map.values():
    ratios[column] = pd.to_numeric(
        ratios[column],
        errors="coerce",
    )


# ---------------------------------------------------------
# Benchmark row
# ---------------------------------------------------------
benchmark = ratios[ratios["company_id"].astype(str) == selected_company]

if benchmark.empty:
    st.warning("Selected company has no ratio data.")
    st.stop()

benchmark = benchmark.iloc[0]


# ---------------------------------------------------------
# Radar chart
# ---------------------------------------------------------
st.subheader(f"{selected_company} vs {selected_group} Average")


metric_names = list(metric_map.keys())
benchmark_values = []
peer_average_values = []


for column in metric_map.values():

    benchmark_value = pd.to_numeric(
        benchmark[column],
        errors="coerce",
    )

    peer_average = pd.to_numeric(
        ratios[column],
        errors="coerce",
    ).mean()

    benchmark_values.append(float(benchmark_value) if pd.notna(benchmark_value) else 0)

    peer_average_values.append(float(peer_average) if pd.notna(peer_average) else 0)


# Radar charts require a closed polygon.
radar_categories = metric_names + [metric_names[0]]

benchmark_radar = benchmark_values + [benchmark_values[0]]
average_radar = peer_average_values + [peer_average_values[0]]


fig = go.Figure()

fig.add_trace(
    go.Scatterpolar(
        r=benchmark_radar,
        theta=radar_categories,
        fill="toself",
        name=selected_company,
    )
)

fig.add_trace(
    go.Scatterpolar(
        r=average_radar,
        theta=radar_categories,
        fill="toself",
        name="Peer Average",
    )
)

fig.update_layout(
    polar={
        "radialaxis": {
            "visible": True,
        }
    },
    height=550,
    margin={"l": 20, "r": 20, "t": 40, "b": 20},
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# Side-by-side peer table
# ---------------------------------------------------------
st.divider()

st.subheader("Peer Group Comparison")


table = ratios[["company_id"] + list(metric_map.values())].copy()

table = table.merge(
    companies[["company_id", "company_name"]],
    on="company_id",
    how="left",
)

table = table.merge(
    peer_df[["company_id", "is_benchmark"]],
    on="company_id",
    how="left",
)

rename_map = {
    "company_id": "Ticker",
    "company_name": "Company",
    "return_on_equity_pct": "ROE",
    "roce_pct": "ROCE",
    "net_profit_margin_pct": "NPM",
    "debt_to_equity": "D/E",
    "free_cash_flow_cr": "FCF",
    "revenue_growth_pct": "Revenue CAGR",
    "net_profit_growth_pct": "PAT CAGR",
    "eps_growth_pct": "EPS CAGR",
    "is_benchmark": "Benchmark",
}

table = table.rename(columns=rename_map)

# Put benchmark first.
table["_benchmark_sort"] = table["Benchmark"].fillna(0).astype(int)

table = table.sort_values(
    ["_benchmark_sort", "Company"],
    ascending=[False, True],
).drop(columns="_benchmark_sort")


# Highlight benchmark row.
def highlight_benchmark(row):
    if row["Benchmark"] == 1:
        return ["font-weight: bold" for _ in row]

    return [""] * len(row)


styled = table.style.apply(
    highlight_benchmark,
    axis=1,
)

st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
)


st.caption("Benchmark company is highlighted when marked in the peer-group database.")
