import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios, get_sectors


ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "nifty100.db"
COMPOSITE_PATH = ROOT_DIR / "output" / "composite_scores.csv"


st.title("Nifty 100 Analytics")
st.caption("Nifty 100 Financial Intelligence Dashboard")


def fmt(value, decimals=2, suffix=""):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}{suffix}"


def load_market_cap(year):
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            return pd.read_sql_query(
                """
                SELECT
                    company_id,
                    year,
                    market_cap_crore,
                    pe_ratio,
                    pb_ratio,
                    ev_ebitda,
                    dividend_yield_pct
                FROM market_cap
                WHERE year = ?
                """,
                conn,
                params=[year],
            )
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------
# Load base data
# ---------------------------------------------------------
companies = get_companies()
sectors = get_sectors()

if COMPOSITE_PATH.exists():
    composite = pd.read_csv(COMPOSITE_PATH)
else:
    composite = pd.DataFrame()


# ---------------------------------------------------------
# Year selector
# ---------------------------------------------------------
years = sorted(
    pd.to_numeric(composite["year"], errors="coerce").dropna().astype(int).unique()
) if not composite.empty else [2024]

selected_year = st.sidebar.selectbox(
    "Analysis Year",
    years,
    index=years.index(2024) if 2024 in years else len(years) - 1,
)


# ---------------------------------------------------------
# Selected-year composite data
# ---------------------------------------------------------
if not composite.empty:
    selected = composite[
        pd.to_numeric(composite["year"], errors="coerce") == selected_year
    ].copy()

    if selected.empty:
        selected = composite.copy()
else:
    selected = pd.DataFrame()


# ---------------------------------------------------------
# Ratio data
# ---------------------------------------------------------
ratio_frames = []

for company_id in companies["company_id"].astype(str):
    df = get_ratios(company_id, selected_year)

    if not df.empty:
        ratio_frames.append(df)

ratios = (
    pd.concat(ratio_frames, ignore_index=True)
    if ratio_frames
    else pd.DataFrame()
)


# ---------------------------------------------------------
# Market data
# ---------------------------------------------------------
market = load_market_cap(selected_year)


# ---------------------------------------------------------
# KPI calculations
# ---------------------------------------------------------
if not selected.empty:
    avg_roe = pd.to_numeric(
        selected["return_on_equity_pct"], errors="coerce"
    ).mean()

    median_de = pd.to_numeric(
        selected["debt_to_equity"], errors="coerce"
    ).median()

    median_revenue_cagr = pd.to_numeric(
        selected["revenue_cagr_5yr_pct"], errors="coerce"
    ).median()
else:
    avg_roe = None
    median_de = None
    median_revenue_cagr = None


median_pe = (
    pd.to_numeric(market["pe_ratio"], errors="coerce").median()
    if not market.empty
    else None
)


if not ratios.empty and "total_debt_cr" in ratios.columns:
    debt = pd.to_numeric(ratios["total_debt_cr"], errors="coerce")
    debt_free = int((debt.fillna(0) <= 0).sum())
else:
    debt_free = 0


# ---------------------------------------------------------
# KPI row
# ---------------------------------------------------------
st.subheader(f"Portfolio Snapshot — {selected_year}")

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Average ROE", fmt(avg_roe, 2, "%"))
c2.metric("Median P/E", fmt(median_pe, 2, "x"))
c3.metric("Median D/E", fmt(median_de, 2, "x"))
c4.metric("Total Companies", f"{len(companies):,}")
c5.metric("Median Revenue CAGR 5Y", fmt(median_revenue_cagr, 2, "%"))
c6.metric("Debt-Free Companies", f"{debt_free:,}")


st.divider()


# ---------------------------------------------------------
# Two-column section
# ---------------------------------------------------------
left, right = st.columns(2)


# ---------------------------------------------------------
# Sector donut
# ---------------------------------------------------------
with left:
    st.subheader("Sector Breakdown")

    if sectors.empty:
        st.warning("No sector data available.")
    else:
        sector_counts = (
            sectors.groupby("broad_sector", dropna=False)
            .size()
            .reset_index(name="company_count")
            .sort_values("company_count", ascending=False)
        )

        sector_counts["broad_sector"] = (
            sector_counts["broad_sector"]
            .fillna("Unknown")
            .astype(str)
        )

        fig = px.pie(
            sector_counts,
            names="broad_sector",
            values="company_count",
            hole=0.5,
        )

        fig.update_layout(
            height=450,
            margin=dict(l=10, r=10, t=20, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# Top 5 composite score
# ---------------------------------------------------------
with right:
    st.subheader("Top 5 Companies by Composite Quality Score")

    if selected.empty:
        st.warning("No composite score data available.")
    else:
        top5 = (
            selected[
                [
                    "company_id",
                    "broad_sector",
                    "composite_quality_score",
                ]
            ]
            .copy()
            .sort_values(
                "composite_quality_score",
                ascending=False,
            )
            .head(5)
        )

        top5["composite_quality_score"] = pd.to_numeric(
            top5["composite_quality_score"],
            errors="coerce",
        ).round(2)

        top5 = top5.rename(
            columns={
                "company_id": "Ticker",
                "broad_sector": "Sector",
                "composite_quality_score": "Composite Score",
            }
        )

        st.dataframe(
            top5,
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------
# Market health
# ---------------------------------------------------------
st.divider()

st.subheader("Market Health")

if median_pe is None:
    st.info(f"No P/E data available for {selected_year}.")
elif median_pe > 30:
    st.warning(
        f"Median P/E is {median_pe:.2f}x for {selected_year}, "
        "indicating a relatively high valuation environment."
    )
elif median_pe < 15:
    st.success(
        f"Median P/E is {median_pe:.2f}x for {selected_year}, "
        "indicating a relatively lower valuation environment."
    )
else:
    st.info(
        f"Median P/E is {median_pe:.2f}x for {selected_year}, "
        "indicating a moderate valuation environment."
    )


st.caption(
    "Data source: Nifty 100 SQLite database and Sprint 3 composite score output."
)