import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator, MinuteLocator
from datetime import datetime, timedelta, timezone, time as dtime
import os

# ---------------- IST Timezone Setup ----------------
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# ---------------- Config ----------------
st.set_page_config(page_title="Live Charts (Nifty 500)", layout="wide")
st.title("📈 Live Intraday Charts — Nifty 500")
st.markdown(f"📅 **Date:** {today_str}  🕘 **Data from 9:00 AM IST onwards**")

# ---------------- Load Tickers ----------------
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
st.markdown(f"🔢 **Total Tickers Loaded:** {len(tickers)}")

# ---------------- Data Fetch ----------------
@st.cache_data(ttl=600)
def fetch_today_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        df = df[df.index.tz_convert(IST).date == now_ist.date()]
        df = df[df.index.tz_convert(IST).time >= dtime(9, 0)]
        return df
    except Exception:
        return pd.DataFrame()

# ---------------- Download & Plot ----------------
if st.button("📥 Load Live Data Now"):
    st.session_state.live_data = {}
    bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        df = fetch_today_data(ticker)
        if not df.empty:
            st.session_state.live_data[ticker] = df
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Live intraday data loaded!")

# ---------------- Show Charts ----------------
if "live_data" not in st.session_state or not st.session_state.live_data:
    st.info("📌 Click the button above to load live intraday charts.")
else:
    empty = True
    for i in range(0, len(st.session_state.live_data), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(st.session_state.live_data):
                break
            symbol = list(st.session_state.live_data.keys())[idx]
            df = st.session_state.live_data[symbol]

            if df is None or df.empty:
                continue

            df.index = df.index.tz_convert(IST)
            empty = False
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            ax.set_title(symbol, fontsize=10)
            ax.set_ylabel("Price", fontsize=9)

            # Set X-axis ticks every 15 min
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))

            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

    if empty:
        st.warning("⚠️ No live data returned for any ticker.")
