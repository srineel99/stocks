import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import MonthLocator, DateFormatter
from datetime import datetime, timedelta, timezone
import os

# ─────────────────────────────────────────────────────
# Timezone setup (IST)
# ─────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))

def get_cache_date() -> str:
    """Return today's date if after 3:45 PM IST, else yesterday."""
    now = datetime.now(IST)
    cutoff = now.replace(hour=15, minute=45, second=0, microsecond=0)
    return now.date().isoformat() if now >= cutoff else (now.date() - timedelta(days=1)).isoformat()

CACHE_DATE = get_cache_date()

# ─────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────
st.set_page_config(page_title="Stock Charts (5Y Weekly)", layout="wide")
st.title("📆 5-Year Weekly Close-Price Charts (Nifty 500)")

# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
@st.cache_data(ttl=24*3600)
def download_data(ticker: str, cache_date: str) -> pd.DataFrame:
    """Fetch 5 years of weekly adjusted stock price."""
    return yf.download(
        ticker,
        period="5y",
        interval="1wk",
        progress=False,
        auto_adjust=True
    )

@st.cache_data(ttl=24*3600)
def get_company_name(ticker: str, cache_date: str) -> str:
    """Get full company name or fallback to ticker."""
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker

def load_tickers() -> list[str]:
    """Load tickers from local file, relative path safe for Streamlit Cloud."""
    base_dir = os.path.dirname(__file__)
    file_path = os.path.abspath(os.path.join(base_dir, "..", "data", "Charts-data", "tickers_Nifty500.txt"))
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

# ─────────────────────────────────────────────────────
# Load ticker list & show metadata
# ─────────────────────────────────────────────────────
tickers = load_tickers()
st.markdown(f"**🧾 Total Tickers:** {len(tickers)}")
st.markdown(f"**📅 Last Refreshed:** {CACHE_DATE} *(updates daily post 3:45 PM IST)*")

# ─────────────────────────────────────────────────────
# Download all button
# ─────────────────────────────────────────────────────
if st.button("📥 Download Weekly Data for All Tickers"):
    st.session_state.data = {}
    progress = st.progress(0)
    for i, symbol in enumerate(tickers):
        df = download_data(symbol, CACHE_DATE)
        st.session_state.data[symbol] = df
        progress.progress((i + 1) / len(tickers))
    st.success("✅ Weekly data downloaded successfully!")

# Ensure session dict exists
if "data" not in st.session_state:
    st.session_state.data = {}

# ─────────────────────────────────────────────────────
# Plot weekly charts in a 2-column layout
# ─────────────────────────────────────────────────────
for idx in range(0, len(tickers), 2):
    cols = st.columns(2)
    for col_i in range(2):
        if idx + col_i >= len(tickers):
            break

        symbol = tickers[idx + col_i]
        df = st.session_state.data.get(symbol)
        if df is None or df.empty:
            cols[col_i].warning(f"No data for {symbol}. Click 📥 Download above.")
            continue

        name = get_company_name(symbol, CACHE_DATE)
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(df.index, df["Close"], linewidth=1)
        ax.set_title(f"{symbol} — {name}", fontsize=11)
        ax.set_ylabel("Close", fontsize=9)
        ax.xaxis.set_major_locator(MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(DateFormatter("%b %Y"))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
        plt.tight_layout()
        cols[col_i].pyplot(fig)
        plt.close(fig)
