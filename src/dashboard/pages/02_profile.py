import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_pl,
    get_pros_cons,
    get_ratios,
)

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "nifty100.db"


st.title("Company Profile")
st.caption("Detailed financial profile, trends, and pros & cons")


def fmt(value, decimals=2, suffix=""):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}{suffix}"


def search_companies(query: str) -> pd.DataFrame:
    companies = get_companies().copy()

    if not query:
        return companies.head(10)

    query = query.lower().strip()

    mask = companies["company_id"].astype(str).str.lower().str.contains(
        query, na=False
    ) | companies["company_name"].astype(str).str.lower().str.contains(query, na=False)

    return companies.loc[mask].head(10)


def get_sector_info(ticker: str) -> tuple[str, str]:
    with sqlite3.connect(str(DB_PATH)) as conn:
        result = pd.read_sql_query(
            """
            SELECT broad_sector, sub_sector
            FROM sectors
            WHERE company_id = ?
            LIMIT 1
            """,
            conn,
            params=[ticker],
        )

    if result.empty:
        return "N/A", "N/A"

    return (
        str(result.iloc[0]["broad_sector"]),
        str(result.iloc[0]["sub_sector"]),
    )


def get_market_cap_latest(ticker: str):
    with sqlite3.connect(str(DB_PATH)) as conn:
        result = pd.read_sql_query(
            """
            SELECT market_cap_crore, pe_ratio, pb_ratio, ev_ebitda
            FROM market_cap
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            conn,
            params=[ticker],
        )

    return result


# ---------------------------------------------------------
# Company search
# ---------------------------------------------------------
companies = get_companies()

st.subheader("Search Company")

query = st.text_input(
    "Type company name or NSE ticker",
    placeholder="Example: INDIGO or NESTLEIND",
)


matches = search_companies(query)

if matches.empty:
    st.error("Ticker not found — please try another.")
    st.stop()


options = [f"{row.company_id} — {row.company_name}" for row in matches.itertuples()]

selected_label = st.selectbox(
    "Select company",
    options,
)

selected_ticker = selected_label.split(" — ", 1)[0]


company = companies[companies["company_id"].astype(str) == selected_ticker].iloc[0]


# ---------------------------------------------------------
# Company details
# ---------------------------------------------------------
sector, sub_sector = get_sector_info(selected_ticker)

st.divider()

st.header(company["company_name"])

c1, c2, c3 = st.columns(3)

with c1:
    st.write("**NSE Ticker**")
    st.write(selected_ticker)

with c2:
    st.write("**Sector**")
    st.write(sector)

with c3:
    st.write("**Sub-sector**")
    st.write(sub_sector)


about = company.get("about_company")

if pd.notna(about) and str(about).strip():
    st.write(str(about))
else:
    st.info("Company description is not available.")


# ---------------------------------------------------------
# Latest financial data
# ---------------------------------------------------------
ratios = get_ratios(selected_ticker)

if ratios.empty:
    st.warning("Financial ratio data is not available for this company.")
    st.stop()


ratios = ratios.copy()
ratios["year"] = pd.to_numeric(ratios["year"], errors="coerce")
ratios = ratios.sort_values("year")

latest = ratios.iloc[-1]


# ---------------------------------------------------------
# 6 KPI tiles
# ---------------------------------------------------------
st.subheader(f"Key Metrics — {int(latest['year'])}")

k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)

with k1:
    st.metric(
        "ROE",
        fmt(latest.get("return_on_equity_pct"), 2, "%"),
    )

with k2:
    st.metric(
        "ROCE",
        fmt(latest.get("roce_pct"), 2, "%"),
    )

with k3:
    st.metric(
        "Net Profit Margin",
        fmt(latest.get("net_profit_margin_pct"), 2, "%"),
    )

with k4:
    st.metric(
        "D/E",
        fmt(latest.get("debt_to_equity"), 2, "x"),
    )

with k5:
    # Calculate 5Y revenue CAGR from P&L if possible.
    pl = get_pl(selected_ticker)

    revenue_cagr = None

    if not pl.empty and "sales" in pl.columns:
        pl = pl.copy()
        pl["year"] = pd.to_numeric(pl["year"], errors="coerce")
        pl["sales"] = pd.to_numeric(pl["sales"], errors="coerce")
        pl = pl.dropna(subset=["year", "sales"]).sort_values("year")

        if len(pl) >= 6:
            start = pl.iloc[-6]["sales"]
            end = pl.iloc[-1]["sales"]

            if start > 0 and end > 0:
                revenue_cagr = ((end / start) ** (1 / 5) - 1) * 100

    st.metric(
        "Revenue CAGR 5Y",
        fmt(revenue_cagr, 2, "%"),
    )

with k6:
    st.metric(
        "FCF",
        fmt(latest.get("free_cash_flow_cr"), 2, " Cr"),
    )


# ---------------------------------------------------------
# Revenue + Net Profit bar chart
# ---------------------------------------------------------
st.divider()
st.subheader("10-Year Revenue and Net Profit")

pl = get_pl(selected_ticker)

if pl.empty:
    st.info("Profit & loss history is unavailable.")
else:
    pl = pl.copy()

    pl["year"] = pd.to_numeric(pl["year"], errors="coerce")
    pl["sales"] = pd.to_numeric(pl["sales"], errors="coerce")
    pl["net_profit"] = pd.to_numeric(pl["net_profit"], errors="coerce")

    pl = pl.dropna(subset=["year"]).sort_values("year").tail(10)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=pl["year"].astype(int),
            y=pl["sales"],
            name="Revenue",
        )
    )

    fig.add_trace(
        go.Bar(
            x=pl["year"].astype(int),
            y=pl["net_profit"],
            name="Net Profit",
        )
    )

    fig.update_layout(
        barmode="group",
        height=450,
        xaxis_title="Year",
        yaxis_title="Amount (₹ Cr)",
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ---------------------------------------------------------
# ROE / ROCE dual-axis line chart
# ---------------------------------------------------------
st.subheader("ROE and ROCE Trend")

trend = ratios[
    [
        "year",
        "return_on_equity_pct",
        "roce_pct",
    ]
].copy()

trend["return_on_equity_pct"] = pd.to_numeric(
    trend["return_on_equity_pct"],
    errors="coerce",
)

trend["roce_pct"] = pd.to_numeric(
    trend["roce_pct"],
    errors="coerce",
)

trend = trend.dropna(subset=["year"]).sort_values("year").tail(10)

if trend.empty:
    st.info("ROE/ROCE trend data is unavailable.")
else:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=trend["year"].astype(int),
            y=trend["return_on_equity_pct"],
            mode="lines+markers",
            name="ROE",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=trend["year"].astype(int),
            y=trend["roce_pct"],
            mode="lines+markers",
            name="ROCE",
            yaxis="y2",
        )
    )

    fig.update_layout(
        height=450,
        xaxis={"title": "Year"},
        yaxis={"title": "ROE (%)"},
        yaxis2={
            "title": "ROCE (%)",
            "overlaying": "y",
            "side": "right",
        },
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Pros and Cons
# ---------------------------------------------------------
st.divider()
st.subheader("Pros & Cons")

pros_cons = get_pros_cons(selected_ticker)

left, right = st.columns(2)

if pros_cons.empty:
    left.info("Pros data is unavailable.")
    right.info("Cons data is unavailable.")
else:
    row = pros_cons.iloc[0]

    with left:
        st.markdown("### Pros")

        pros = str(row.get("pros", "") or "")
        pros_items = [
            item.strip()
            for item in pros.replace(";", "\n").splitlines()
            if item.strip()
        ]

        if pros_items:
            for item in pros_items:
                st.success(f"✓ {item}")
        else:
            st.info("No pros available.")

    with right:
        st.markdown("### Cons")

        cons = str(row.get("cons", "") or "")
        cons_items = [
            item.strip()
            for item in cons.replace(";", "\n").splitlines()
            if item.strip()
        ]

        if cons_items:
            for item in cons_items:
                st.error(f"✗ {item}")
        else:
            st.info("No cons available.")


st.caption("Data source: Nifty 100 SQLite database.")
