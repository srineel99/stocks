import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
import os
import random

# --- IST Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Page config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing **{today_str}** data — Starting from first available tick after 9:00 AM IST")

# --- Load tickers from file ---
@st.cache_data
def load_tickers():
    path = "data/Charts-data/tickers_Nifty500.txt"
    if not os.path.exists(path):
        st.error(f"Ticker file not found: {path}")
        return []
    with open(path) as f:
        return [
            line.strip().upper() if line.strip().upper().endswith(".NS")
            else line.strip().upper() + ".NS"
            for line in f if line.strip()
        ]

tickers = load_tickers()
st.markdown(f"📈 **Total Tickers:** {len(tickers)}")

# --- Download intraday data (cached) ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        df = df.tz_convert(IST).tz_localize(None)  # Convert to IST and make naive
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except:
        return pd.DataFrame()

# --- Trigger Download ---
if "intraday_data" not in st.session_state:
    st.info("📥 Fetching live intraday data (1m interval)...")
    st.session_state.intraday_data = {}
    bar = st.progress(0)
    random.shuffle(tickers)  # Shuffle to avoid same order every time
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            st.session_state.intraday_data[ticker] = df
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Live intraday data loaded!")

# --- Plot Charts ---
if st.session_state.intraday_data:
    data = st.session_state.intraday_data
    count = 0
    for i in range(0, len(data), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j >= len(data):
                break
            symbol = list(data.keys())[i + j]
            df = data[symbol]

            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            ax.set_title(symbol, fontsize=10)
            ax.set_ylabel("Price", fontsize=9)

            # X-axis ticks at 15-minute intervals
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)

            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)
            count += 1

    if count == 0:
        st.warning("⚠️ No valid intraday data returned. Try again later.")
else:
    st.warning("⚠️ Data not loaded. Please refresh the page.")
