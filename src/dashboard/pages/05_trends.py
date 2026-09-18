import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios

st.title("Trend Analysis")
st.caption("Explore up to three financial metrics across a company's historical years.")


# ---------------------------------------------------------
# Company search
# ---------------------------------------------------------
companies = get_companies().copy()

query = st.text_input(
    "Search company",
    placeholder="Type company name or ticker",
)

if query:
    q = query.strip().lower()

    matches = companies[
        companies["company_id"].astype(str).str.lower().str.contains(q, na=False)
        | companies["company_name"].astype(str).str.lower().str.contains(q, na=False)
    ].copy()
else:
    matches = companies.copy()


if matches.empty:
    st.error("Ticker not found — please try another.")
    st.stop()


matches["label"] = (
    matches["company_id"].astype(str) + " — " + matches["company_name"].astype(str)
)

selected_label = st.selectbox(
    "Select company",
    matches["label"].tolist(),
)

ticker = selected_label.split(" — ", 1)[0]


# ---------------------------------------------------------
# Load ratio history
# ---------------------------------------------------------
ratios = get_ratios(ticker)

if ratios.empty:
    st.warning("Historical ratio data is unavailable for this company.")
    st.stop()


ratios = ratios.copy()

ratios["year"] = pd.to_numeric(
    ratios["year"],
    errors="coerce",
)

ratios = ratios.dropna(subset=["year"]).sort_values("year")


# ---------------------------------------------------------
# Metric selection
# ---------------------------------------------------------
metric_map = {
    "ROE (%)": "return_on_equity_pct",
    "ROCE (%)": "roce_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Operating Profit Margin (%)": "operating_profit_margin_pct",
    "D/E (x)": "debt_to_equity",
    "Interest Coverage (x)": "interest_coverage",
    "Revenue Growth (%)": "revenue_growth_pct",
    "PAT Growth (%)": "net_profit_growth_pct",
    "EPS Growth (%)": "eps_growth_pct",
    "FCF Margin (%)": "free_cash_flow_margin_pct",
}


selected_metrics = st.multiselect(
    "Select up to 3 metrics",
    options=list(metric_map.keys()),
    default=["ROE (%)"],
    max_selections=3,
)


if not selected_metrics:
    st.info("Select at least one metric.")
    st.stop()


# ---------------------------------------------------------
# Chart
# ---------------------------------------------------------
st.subheader(f"{ticker} — Historical Trend")

fig = go.Figure()


for metric_name in selected_metrics:
    column = metric_map[metric_name]

    if column not in ratios.columns:
        continue

    values = pd.to_numeric(
        ratios[column],
        errors="coerce",
    )

    chart_df = pd.DataFrame(
        {
            "year": ratios["year"],
            "value": values,
        }
    ).dropna()

    if chart_df.empty:
        continue

    fig.add_trace(
        go.Scatter(
            x=chart_df["year"].astype(int),
            y=chart_df["value"],
            mode="lines+markers+text",
            name=metric_name,
            text=[
                f"{v:.1f}%" if "x)" not in metric_name else f"{v:.2f}x"
                for v in chart_df["value"]
            ],
            textposition="top center",
        )
    )


fig.update_layout(
    height=550,
    hovermode="x unified",
    xaxis_title="Year",
    yaxis_title="Metric Value",
    margin={"l": 20, "r": 20, "t": 40, "b": 20},
)

st.plotly_chart(
    fig,
    width="stretch",
)


# ---------------------------------------------------------
# YoY change table
# ---------------------------------------------------------
st.divider()

st.subheader("Year-over-Year Change")

yoy = ratios[["year"]].copy()

for metric_name in selected_metrics:
    column = metric_map[metric_name]

    if column not in ratios.columns:
        continue

    values = pd.to_numeric(
        ratios[column],
        errors="coerce",
    )

    yoy[metric_name] = values.pct_change() * 100


yoy = yoy.sort_values("year", ascending=False)

st.dataframe(
    yoy.round(2),
    width="stretch",
    hide_index=True,
)


# ---------------------------------------------------------
# Data availability note
# ---------------------------------------------------------
year_count = ratios["year"].nunique()

if year_count < 10:
    st.info(
        f"Historical data available for {year_count} years. "
        "The chart displays all available data."
    )
else:
    st.caption("Displaying the latest 10 years of available historical data.")

