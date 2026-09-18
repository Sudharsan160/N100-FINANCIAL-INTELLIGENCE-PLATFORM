import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_sectors

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "nifty100.db"

st.title("Sector Analysis")
st.caption("Explore company performance within each Nifty 100 sector.")


# ---------------------------------------------------------
# Load sector data
# ---------------------------------------------------------
sectors = get_sectors().copy()

if sectors.empty:
    st.error("Sector data is unavailable.")
    st.stop()


sector_names = (
    sectors["broad_sector"].dropna().astype(str).sort_values().unique().tolist()
)

selected_sector = st.selectbox(
    "Select Sector",
    sector_names,
)


sector_companies = sectors[
    sectors["broad_sector"].astype(str) == selected_sector
].copy()


# ---------------------------------------------------------
# Load latest financial data
# ---------------------------------------------------------
company_ids = sector_companies["company_id"].astype(str).tolist()

placeholders = ",".join(["?"] * len(company_ids))

try:
    with sqlite3.connect(str(DB_PATH)) as conn:
        financial = pd.read_sql_query(
            f"""
            SELECT
                fr.company_id,
                fr.year,
                fr.return_on_equity_pct,
                fr.return_on_assets_pct,
                fr.net_profit_margin_pct,
                fr.operating_profit_margin_pct,
                fr.revenue_growth_pct,
                fr.free_cash_flow_cr,
                mc.market_cap_crore
            FROM financial_ratios fr
            LEFT JOIN market_cap mc
                ON mc.company_id = fr.company_id
               AND mc.year = fr.year
            WHERE fr.company_id IN ({placeholders})
            """,
            conn,
            params=company_ids,
        )
except Exception:  # noqa: BLE001
    financial = pd.DataFrame()


if financial.empty:
    st.warning("Financial data is unavailable for this sector.")
    st.stop()


# Latest available year per company
financial["year"] = pd.to_numeric(
    financial["year"],
    errors="coerce",
)

financial = financial.sort_values(["company_id", "year"])

financial = financial.groupby("company_id", as_index=False).tail(1)


# ---------------------------------------------------------
# Merge sector metadata
# ---------------------------------------------------------
data = sector_companies.merge(
    financial,
    on="company_id",
    how="left",
)


# ---------------------------------------------------------
# Convert numeric fields
# ---------------------------------------------------------
for column in [
    "return_on_equity_pct",
    "net_profit_margin_pct",
    "free_cash_flow_cr",
    "market_cap_crore",
]:
    if column in data.columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )


# ---------------------------------------------------------
# Company bubble chart
# ---------------------------------------------------------
st.subheader(f"{selected_sector} — Companies")

chart_data = data.copy()

chart_data["Revenue"] = pd.NA

# Revenue is not stored directly in financial_ratios.
# Retrieve sales from profitandloss.
try:
    with sqlite3.connect(str(DB_PATH)) as conn:
        pl = pd.read_sql_query(
            f"""
            SELECT
                company_id,
                year,
                sales
            FROM profitandloss
            WHERE company_id IN ({placeholders})
            """,
            conn,
            params=company_ids,
        )

    pl["year"] = pd.to_numeric(
        pl["year"],
        errors="coerce",
    )

    pl["sales"] = pd.to_numeric(
        pl["sales"],
        errors="coerce",
    )

    pl = (
        pl.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    chart_data = chart_data.drop(columns=["Revenue"])

    chart_data = chart_data.merge(
        pl[["company_id", "sales"]],
        on="company_id",
        how="left",
    )

    chart_data = chart_data.rename(columns={"sales": "Revenue"})

except Exception:  # noqa: BLE001
    chart_data["Revenue"] = pd.NA


# Company names
with sqlite3.connect(str(DB_PATH)) as conn:
    company_names = pd.read_sql_query(
        f"""
        SELECT id AS company_id, company_name
        FROM companies
        WHERE id IN ({placeholders})
        """,
        conn,
        params=company_ids,
    )


chart_data = chart_data.merge(
    company_names,
    on="company_id",
    how="left",
)


# ---------------------------------------------------------
# Bubble chart
# ---------------------------------------------------------
bubble = chart_data.dropna(subset=["Revenue", "return_on_equity_pct"]).copy()

if bubble.empty:
    st.info("Not enough data to create the sector bubble chart.")
else:
    fig = px.scatter(
        bubble,
        x="Revenue",
        y="return_on_equity_pct",
        size="market_cap_crore",
        color="sub_sector",
        hover_name="company_name",
        hover_data=[
            "company_id",
            "Revenue",
            "return_on_equity_pct",
            "market_cap_crore",
        ],
        size_max=55,
    )

    fig.update_layout(
        height=600,
        xaxis_title="Revenue (₹ Cr)",
        yaxis_title="ROE (%)",
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Sector median KPIs
# ---------------------------------------------------------
st.divider()

st.subheader(f"{selected_sector} — Median KPIs")

kpi_rows = []

for label, column in [
    ("ROE", "return_on_equity_pct"),
    ("NPM", "net_profit_margin_pct"),
    ("OPM", "operating_profit_margin_pct"),
    ("Revenue Growth", "revenue_growth_pct"),
    ("FCF", "free_cash_flow_cr"),
]:
    if column in data.columns:
        value = pd.to_numeric(
            data[column],
            errors="coerce",
        ).median()

        kpi_rows.append(
            {
                "Metric": label,
                "Sector Median": value,
            }
        )


kpi_df = pd.DataFrame(kpi_rows)

if kpi_df.empty:
    st.info("Sector KPI data is unavailable.")
else:
    fig_kpi = px.bar(
        kpi_df,
        x="Metric",
        y="Sector Median",
        text_auto=".2f",
    )

    fig_kpi.update_layout(
        height=400,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )

    st.plotly_chart(
        fig_kpi,
        use_container_width=True,
    )


st.caption(f"Companies in selected sector: {len(sector_companies)}")
