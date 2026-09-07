import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_companies


ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "nifty100.db"


st.title("Capital Allocation Map")
st.caption(
    "Nifty 100 companies grouped by cash-flow-based capital allocation pattern."
)


# ---------------------------------------------------------
# Load company list
# ---------------------------------------------------------
companies = get_companies()


# ---------------------------------------------------------
# Load cash-flow + balance-sheet data
# ---------------------------------------------------------
with sqlite3.connect(str(DB_PATH)) as conn:

    cf = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity
        FROM cashflow
        """,
        conn,
    )

    bs = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            borrowings
        FROM balancesheet
        """,
        conn,
    )


if cf.empty:
    st.error("Cash-flow data is unavailable.")
    st.stop()


# ---------------------------------------------------------
# Latest cash-flow year per company
# ---------------------------------------------------------
cf["year"] = pd.to_numeric(
    cf["year"],
    errors="coerce",
)

for column in [
    "operating_activity",
    "investing_activity",
    "financing_activity",
]:
    cf[column] = pd.to_numeric(
        cf[column],
        errors="coerce",
    )


cf = cf.dropna(subset=["year"])

latest_cf = (
    cf.sort_values(["company_id", "year"])
    .groupby("company_id", as_index=False)
    .tail(1)
)


# ---------------------------------------------------------
# Latest balance-sheet year
# ---------------------------------------------------------
if not bs.empty:

    bs["year"] = pd.to_numeric(
        bs["year"],
        errors="coerce",
    )

    bs["borrowings"] = pd.to_numeric(
        bs["borrowings"],
        errors="coerce",
    )

    bs = bs.dropna(subset=["year"])

    latest_bs = (
        bs.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

else:
    latest_bs = pd.DataFrame()


# ---------------------------------------------------------
# Capital allocation classification
# ---------------------------------------------------------
def classify_pattern(row):

    cfo = row["operating_activity"]
    cfi = row["investing_activity"]
    cff = row["financing_activity"]

    if pd.isna(cfo) or pd.isna(cfi) or pd.isna(cff):
        return "Data Unavailable"

    # Strong operating cash generation
    if cfo > 0 and cfi < 0 and cff < 0:
        return "Self-Funded Growth"

    if cfo > 0 and cfi < 0 and cff > 0:
        return "Growth + External Funding"

    if cfo > 0 and cfi > 0 and cff < 0:
        return "Shareholder Returns"

    if cfo > 0 and cfi > 0 and cff > 0:
        return "Cash Accumulator"

    # Negative operating cash flow
    if cfo < 0 and cfi < 0 and cff > 0:
        return "Distress / Funding Need"

    if cfo < 0 and cfi > 0 and cff > 0:
        return "Asset Monetisation"

    if cfo < 0 and cfi < 0 and cff < 0:
        return "Cash Burn"

    if cfo < 0 and cfi > 0 and cff < 0:
        return "Restructuring"

    return "Mixed"


latest_cf["capital_allocation_pattern"] = latest_cf.apply(
    classify_pattern,
    axis=1,
)


# ---------------------------------------------------------
# Merge company names
# ---------------------------------------------------------
data = latest_cf.merge(
    companies[
        ["company_id", "company_name"]
    ],
    on="company_id",
    how="left",
)


# ---------------------------------------------------------
# Treemap
# ---------------------------------------------------------
st.subheader("Capital Allocation Patterns")

pattern_counts = (
    data.groupby("capital_allocation_pattern")
    .size()
    .reset_index(name="company_count")
    .sort_values("company_count", ascending=False)
)


fig = px.treemap(
    pattern_counts,
    path=["capital_allocation_pattern"],
    values="company_count",
)

fig.update_layout(
    height=500,
    margin=dict(l=10, r=10, t=30, b=10),
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# Pattern selector
# ---------------------------------------------------------
st.divider()

st.subheader("Companies in Selected Pattern")

patterns = (
    data["capital_allocation_pattern"]
    .dropna()
    .astype(str)
    .sort_values()
    .unique()
    .tolist()
)

selected_pattern = st.selectbox(
    "Select Pattern",
    patterns,
)


selected_companies = data[
    data["capital_allocation_pattern"] == selected_pattern
].copy()


# ---------------------------------------------------------
# Company list
# ---------------------------------------------------------
display_columns = [
    "company_id",
    "company_name",
    "operating_activity",
    "investing_activity",
    "financing_activity",
]

display_columns = [
    col
    for col in display_columns
    if col in selected_companies.columns
]


st.dataframe(
    selected_companies[display_columns],
    use_container_width=True,
    hide_index=True,
)


st.caption(
    f"{len(selected_companies)} companies in "
    f"the '{selected_pattern}' pattern."
)