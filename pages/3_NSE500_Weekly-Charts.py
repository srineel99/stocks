import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import MonthLocator, DateFormatter
from datetime import datetime, timedelta, timezone

# --- Timezone setup for IST (UTC+5:30) -----------------------------------
IST = timezone(timedelta(hours=5, minutes=30))

def get_cache_date() -> str:
    """
    Returns a date-string to use as cache key:
    - If now ≥15:45 IST, return today;
    - else return yesterday.
    Ensures we refresh data once daily after market close.
    """
    now = datetime.now(IST)
    cutoff = now.replace(hour=15, minute=45, second=0, microsecond=0)
    if now >= cutoff:
        return now.date().isoformat()
    else:
        return (now.date() - timedelta(days=1)).isoformat()

CACHE_DATE = get_cache_date()

st.set_page_config(page_title="Stock Charts (5Y Weekly)", layout="wide")
st.title("🔄 5-Year Weekly Close-Price Charts (All Tickers)")

# --- Helpers -------------------------------------------------------------
@st.cache_data(ttl=24*3600)
def download_data(ticker: str, cache_date: str) -> pd.DataFrame:
    """
    Fetch 5 years of weekly adjusted data for a ticker.
    """
    df = yf.download(
        ticker,
        period="5y",
        interval="1wk",
        progress=False,
        auto_adjust=True
    )
    return df

@st.cache_data(ttl=24*3600)
def get_company_name(ticker: str, cache_date: str) -> str:
    """
    Lookup the longName (company name) for a ticker, fallback to symbol.
    """
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker

def load_tickers(file_path="/data/Charts-data/tickers_Nitfy500.txt") -> list[str]:
    """
    Load list of Nifty500 tickers from a text file (one symbol per line).
    """
    with open(file_path) as f:
        return [line.strip() for line in f if line.strip()]

# --- Load and display count ---------------------------------------------
tickers = load_tickers()
st.markdown(f"**Total tickers:** {len(tickers)}")
st.markdown(f"**Data last refreshed for:** {CACHE_DATE} (updates daily after 3:45 PM IST)")

# --- Download all data button ------------------------------------------
if st.button("Download Data for All Tickers"):
    st.session_state.data = {}
    progress = st.progress(0)
    for i, symbol in enumerate(tickers):
        df = download_data(symbol, CACHE_DATE)
        st.session_state.data[symbol] = df
        progress.progress((i + 1) / len(tickers))
    st.success("All data downloaded!")

# initialize session cache if first run
if "data" not in st.session_state:
    st.session_state.data = {}

# --- Plot all charts in a 2-column grid, scrollable --------------------
for idx in range(0, len(tickers), 2):
    cols = st.columns(2)
    for col_i in range(2):
        if idx + col_i >= len(tickers):
            break

        symbol = tickers[idx + col_i]
        df = st.session_state.data.get(symbol)
        if df is None or df.empty:
            cols[col_i].warning(f"No data for {symbol}. Click Download first.")
            continue

        # fetch company name once daily
        name = get_company_name(symbol, CACHE_DATE)

        # prepare figure
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(df.index, df["Close"], linewidth=1)
        ax.set_title(f"{symbol} — {name}", fontsize=11)
        ax.set_ylabel("Close", fontsize=9)

        # date ticks: every 3 months
        ax.xaxis.set_major_locator(MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(DateFormatter("%b %Y"))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)

        plt.tight_layout()
        cols[col_i].pyplot(fig)
        plt.close(fig)
