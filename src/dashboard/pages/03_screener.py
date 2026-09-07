import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios


st.title("Nifty 100 Screener")
st.caption("Filter companies using financial quality, growth, valuation, and leverage metrics.")


# ---------------------------------------------------------
# Load companies
# ---------------------------------------------------------
companies = get_companies()

# We use the latest available ratio year by default.
all_ratios = []

for ticker in companies["company_id"].dropna().astype(str):
    df = get_ratios(ticker)

    if not df.empty:
        all_ratios.append(df)

if all_ratios:
    ratios = pd.concat(all_ratios, ignore_index=True)
else:
    ratios = pd.DataFrame()


if ratios.empty:
    st.error("No financial ratio data is available.")
    st.stop()


# Keep latest year for each company
ratios["year"] = pd.to_numeric(ratios["year"], errors="coerce")

ratios = (
    ratios
    .sort_values(["company_id", "year"])
    .groupby("company_id", as_index=False)
    .tail(1)
)


# ---------------------------------------------------------
# Merge company information
# ---------------------------------------------------------
df = ratios.merge(
    companies[["company_id", "company_name"]],
    on="company_id",
    how="left",
)

# Add sectors
from src.dashboard.utils.db import get_sectors

sectors = get_sectors()

df = df.merge(
    sectors[["company_id", "broad_sector", "sub_sector"]],
    on="company_id",
    how="left",
)


# ---------------------------------------------------------
# Metric preparation
# ---------------------------------------------------------
for col in [
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_growth_pct",
    "net_profit_growth_pct",
    "operating_profit_margin_pct",
    "interest_coverage",
]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")


# Add market data
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "nifty100.db"

try:
    with sqlite3.connect(str(DB_PATH)) as conn:
        market = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                pe_ratio,
                pb_ratio,
                dividend_yield_pct
            FROM market_cap
            """,
            conn,
        )

    market["year"] = pd.to_numeric(market["year"], errors="coerce")

    market = (
        market
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    df = df.merge(
        market[
            [
                "company_id",
                "pe_ratio",
                "pb_ratio",
                "dividend_yield_pct",
            ]
        ],
        on="company_id",
        how="left",
    )

except Exception:
    df["pe_ratio"] = pd.NA
    df["pb_ratio"] = pd.NA
    df["dividend_yield_pct"] = pd.NA


# ---------------------------------------------------------
# Composite scores
# ---------------------------------------------------------
composite_path = ROOT_DIR / "output" / "composite_scores.csv"

try:
    composite = pd.read_csv(composite_path)

    composite["year"] = pd.to_numeric(
        composite["year"],
        errors="coerce",
    )

    composite = (
        composite
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    df = df.merge(
        composite[
            [
                "company_id",
                "composite_quality_score",
                "revenue_cagr_5yr_pct",
                "pat_cagr_5yr_pct",
            ]
        ],
        on="company_id",
        how="left",
    )

except Exception:
    df["composite_quality_score"] = pd.NA
    df["revenue_cagr_5yr_pct"] = pd.NA
    df["pat_cagr_5yr_pct"] = pd.NA


# ---------------------------------------------------------
# Presets
# ---------------------------------------------------------
presets = {
    "Quality": {
        "roe": 15.0,
        "de": 2.0,
        "fcf": -100000.0,
        "revenue": 0.0,
        "pat": 0.0,
        "opm": 10.0,
        "pe": 1000.0,
        "pb": 1000.0,
        "dividend": 0.0,
        "icr": 1.5,
    },
    "Value": {
        "roe": 10.0,
        "de": 2.0,
        "fcf": 0.0,
        "revenue": 0.0,
        "pat": 0.0,
        "opm": 0.0,
        "pe": 25.0,
        "pb": 5.0,
        "dividend": 0.0,
        "icr": 1.0,
    },
    "Growth": {
        "roe": 10.0,
        "de": 2.0,
        "fcf": -100000.0,
        "revenue": 15.0,
        "pat": 15.0,
        "opm": 0.0,
        "pe": 1000.0,
        "pb": 1000.0,
        "dividend": 0.0,
        "icr": 1.0,
    },
    "Dividend": {
        "roe": 8.0,
        "de": 2.0,
        "fcf": 0.0,
        "revenue": 0.0,
        "pat": 0.0,
        "opm": 0.0,
        "pe": 1000.0,
        "pb": 1000.0,
        "dividend": 2.0,
        "icr": 1.0,
    },
    "Debt-Free": {
        "roe": 0.0,
        "de": 0.05,
        "fcf": -100000.0,
        "revenue": 0.0,
        "pat": 0.0,
        "opm": 0.0,
        "pe": 1000.0,
        "pb": 1000.0,
        "dividend": 0.0,
        "icr": 1.0,
    },
    "Turnaround": {
        "roe": 0.0,
        "de": 2.0,
        "fcf": 0.0,
        "revenue": 5.0,
        "pat": 5.0,
        "opm": 0.0,
        "pe": 1000.0,
        "pb": 1000.0,
        "dividend": 0.0,
        "icr": 1.0,
    },
}


if "screener_preset" not in st.session_state:
    st.session_state.screener_preset = "Quality"


# ---------------------------------------------------------
# Preset buttons
# ---------------------------------------------------------
st.subheader("Presets")

preset_cols = st.columns(6)

for col, preset_name in zip(preset_cols, presets):
    with col:
        if st.button(
            preset_name,
            use_container_width=True,
        ):
            st.session_state.screener_preset = preset_name
            st.rerun()


preset = presets[st.session_state.screener_preset]


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------
st.sidebar.header("Screener Filters")

roe_min = st.sidebar.slider(
    "ROE minimum (%)",
    0.0,
    1000.0,
    float(preset["roe"]),
)

de_max = st.sidebar.slider(
    "D/E maximum",
    0.0,
    10.0,
    float(preset["de"]),
)

fcf_min = st.sidebar.number_input(
    "FCF minimum (₹ Cr)",
    value=float(preset["fcf"]),
)

revenue_min = st.sidebar.slider(
    "Revenue CAGR 5Y minimum (%)",
    -100.0,
    100.0,
    float(preset["revenue"]),
)

pat_min = st.sidebar.slider(
    "PAT CAGR 5Y minimum (%)",
    -100.0,
    200.0,
    float(preset["pat"]),
)

opm_min = st.sidebar.slider(
    "OPM minimum (%)",
    -100.0,
    100.0,
    float(preset["opm"]),
)

pe_max = st.sidebar.slider(
    "P/E maximum",
    0.0,
    200.0,
    float(min(preset["pe"], 200)),
)

pb_max = st.sidebar.slider(
    "P/B maximum",
    0.0,
    100.0,
    float(min(preset["pb"], 100)),
)

dividend_min = st.sidebar.slider(
    "Dividend Yield minimum (%)",
    0.0,
    20.0,
    float(preset["dividend"]),
)

icr_min = st.sidebar.slider(
    "Interest Coverage minimum",
    0.0,
    100.0,
    float(preset["icr"]),
)


# ---------------------------------------------------------
# Filtering
# ---------------------------------------------------------
filtered = df.copy()


def apply_min(data, column, value):
    if column not in data.columns:
        return data

    values = pd.to_numeric(
        data[column],
        errors="coerce",
    )

    return data[
        values.fillna(float("-inf")) >= value
    ]


def apply_max(data, column, value):
    if column not in data.columns:
        return data

    values = pd.to_numeric(
        data[column],
        errors="coerce",
    )

    return data[
        values.fillna(float("inf")) <= value
    ]


filtered = apply_min(
    filtered,
    "return_on_equity_pct",
    roe_min,
)

filtered = apply_max(
    filtered,
    "debt_to_equity",
    de_max,
)

filtered = apply_min(
    filtered,
    "free_cash_flow_cr",
    fcf_min,
)

filtered = apply_min(
    filtered,
    "revenue_cagr_5yr_pct",
    revenue_min,
)

filtered = apply_min(
    filtered,
    "pat_cagr_5yr_pct",
    pat_min,
)

filtered = apply_min(
    filtered,
    "operating_profit_margin_pct",
    opm_min,
)

filtered = apply_max(
    filtered,
    "pe_ratio",
    pe_max,
)

filtered = apply_max(
    filtered,
    "pb_ratio",
    pb_max,
)

filtered = apply_min(
    filtered,
    "dividend_yield_pct",
    dividend_min,
)

filtered = apply_min(
    filtered,
    "interest_coverage",
    icr_min,
)


# ---------------------------------------------------------
# Results
# ---------------------------------------------------------
st.subheader(
    f"{len(filtered)} companies match your filters"
)

visible_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr_pct",
    "pat_cagr_5yr_pct",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]

visible_columns = [
    col for col in visible_columns
    if col in filtered.columns
]

result = filtered[visible_columns].copy()

st.dataframe(
    result,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# CSV download
# ---------------------------------------------------------
csv_data = result.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Results as CSV",
    data=csv_data,
    file_name="screener_results.csv",
    mime="text/csv",
    use_container_width=True,
)