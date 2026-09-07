import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("pages/01_home.py", title="Home"),
    st.Page("pages/02_profile.py", title="Company Profile"),
    st.Page("pages/03_screener.py", title="Screener"),
    st.Page("pages/04_peers.py", title="Peer Comparison"),
    st.Page("pages/05_trends.py", title="Trend Analysis"),
    st.Page("pages/06_sectors.py", title="Sector Analysis"),
    st.Page("pages/07_capital.py", title="Capital Allocation"),
    st.Page("pages/08_reports.py", title="Annual Reports"),
]

pg = st.navigation(pages)

st.sidebar.markdown("---")
st.sidebar.caption("Nifty 100 Financial Intelligence Platform")
st.sidebar.caption("Sprint 4 - Dashboard & Valuation")

pg.run()