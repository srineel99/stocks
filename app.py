import streamlit as st

# ─────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="📊 Stock Dashboard",
    layout="wide",
)

# ─────────────────────────────────────────────────────
# Main dashboard content
# ─────────────────────────────────────────────────────
st.title("📊 Stock Dashboard")

st.markdown(
    """
    Welcome to your live stock analytics dashboard!  

    Use the **page selector** in the **top-left sidebar** to access:

    - 📈 **NSE500 Charts** — 2-year daily close for all Nifty 500 stocks  
    - 🔄 **Top Gainers / Losers** — Live 1-min charts based on uploaded CSVs  
    - 📅 **NSE500 Weekly-Charts** — Weekly close trends across Nifty 500  
    """
)
