import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "nifty100.db"


st.title("Annual Reports")
st.caption("Browse available annual reports for each Nifty 100 company.")


# ---------------------------------------------------------
# Load companies
# ---------------------------------------------------------
with sqlite3.connect(str(DB_PATH)) as conn:
    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY company_name
        """,
        conn,
    )


if companies.empty:
    st.error("Company data is unavailable.")
    st.stop()


# ---------------------------------------------------------
# Search
# ---------------------------------------------------------
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

company_name = matches.loc[
    matches["company_id"].astype(str) == ticker,
    "company_name",
].iloc[0]


st.divider()

st.header(company_name)
st.caption(f"NSE Ticker: {ticker}")


# ---------------------------------------------------------
# Load reports
# ---------------------------------------------------------
with sqlite3.connect(str(DB_PATH)) as conn:
    reports = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            annual_report
        FROM documents
        WHERE company_id = ?
        ORDER BY year DESC
        """,
        conn,
        params=[ticker],
    )


# ---------------------------------------------------------
# Report display
# ---------------------------------------------------------
st.subheader("Available Annual Reports")


if reports.empty:
    st.warning("No annual reports are available for this company.")
    st.stop()


for _, row in reports.iterrows():

    year = row.get("year")
    url = row.get("annual_report")

    year_text = str(int(year)) if pd.notna(year) else "Unknown Year"

    url_text = str(url).strip() if pd.notna(url) else ""

    with st.container(border=True):

        col1, col2, col3 = st.columns([2, 5, 2])

        with col1:
            st.markdown(f"### {year_text}")

        with col2:
            if url_text and url_text.lower() not in {"none", "null", "nan"}:
                st.markdown(f"[Open BSE Annual Report]({url_text})")
            else:
                st.markdown("No report URL available.")

        with col3:

            if url_text and url_text.lower() not in {"none", "null", "nan"}:
                st.success("Report available")
            else:
                st.error("Report unavailable")


st.caption("Report links are sourced from the documents table.")

