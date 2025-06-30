import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import MonthLocator, DateFormatter
from datetime import datetime, timedelta, timezone
import os

IST = timezone(timedelta(hours=5, minutes=30))

def get_cache_date() -> str:
    now = datetime.now(IST)
    cutoff = now.replace(hour=15, minute=45, second=0, microsecond=0)
    return now.date().isoformat() if now >= cutoff else (now.date() - timedelta(days=1)).isoformat()

CACHE_DATE = get_cache_date()

st.set_page_config(page_title="Stock Charts (5Y Weekly)", layout="wide")
st.title("📆 5-Year Weekly Close-Price Charts (Nifty 500)")

@st.cache_data(ttl=24*3600)
def download_data(ticker: str, cache_date: str) -> pd.DataFrame:
    return yf.download(ticker, period="5y", interval="1wk", progress=False, auto_adjust=True)

@st.cache_data(ttl=24*3600)
def get_company_name(ticker: str, cache_date: str) -> str:
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker

def load_tickers() -> list[str]:
    file_path = "data/Charts-data/tickers_Nifty500.txt"
    if not os.path.exists(file_path):
        st.error(f"Ticker file not found: {file_path}")
        return []
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

tickers = load_tickers()
st.markdown(f"**🧾 Total Tickers:** {len(tickers)}")
st.markdown(f"**📅 Last Refreshed:** {CACHE_DATE} *(updates daily post 3:45 PM IST)*")

if st.button("📥 Download Weekly Data for All Tickers"):
    st.session_state.data = {}
    progress = st.progress(0)
    for i, symbol in enumerate(tickers):
        df = download_data(symbol, CACHE_DATE)
        st.session_state.data[symbol] = df
        progress.progress((i + 1) / len(tickers))
    st.success("✅ Weekly data downloaded successfully!")

if "data" not in st.session_state:
    st.session_state.data = {}

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
