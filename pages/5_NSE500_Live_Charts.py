import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
import numpy as np
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
        df = df.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except:
        return pd.DataFrame()

# --- Classify charts by slope ---
def classify_charts(data):
    ascending = []
    descending = []
    neutral = []

    for symbol, df in data.items():
        if len(df) < 10:
            neutral.append((symbol, df))
            continue

        try:
            x = np.arange(len(df))
            y = df["Close"].values
            slope, _ = np.polyfit(x, y, 1)

            if 0.4 <= slope <= 1.5:
                ascending.append((symbol, df))
            elif -1.5 <= slope <= -0.4:
                descending.append((symbol, df))
            else:
                neutral.append((symbol, df))
        except:
            neutral.append((symbol, df))

    return ascending, descending, neutral

# --- Download Data (First Time Only) ---
if "intraday_data" not in st.session_state:
    st.info("📥 Fetching live intraday data (1m interval)...")
    st.session_state.intraday_data = {}
    bar = st.progress(0)
    random.shuffle(tickers)
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            st.session_state.intraday_data[ticker] = df
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Live intraday data loaded!")

# --- Plot charts grouped ---
def plot_group(title, group_data):
    if group_data:
        st.subheader(title)
        for i in range(0, len(group_data), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j >= len(group_data): break
                symbol, df = group_data[i + j]

                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(df.index, df["Close"], lw=1.2)
                ax.set_title(symbol, fontsize=10)
                ax.set_ylabel("Price", fontsize=9)
                ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
                ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
                plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
                plt.tight_layout()
                cols[j].pyplot(fig)
                plt.close(fig)
    else:
        st.warning(f"No data in group: {title}")

# --- Final display logic ---
if st.session_state.intraday_data:
    data = st.session_state.intraday_data
    ascending, descending, neutral = classify_charts(data)

    plot_group("📈 Ascending (≈ +45°)", ascending)
    plot_group("📉 Descending (≈ -45°)", descending)
    plot_group("➖ Neutral / Flat Charts", neutral)

else:
    st.warning("⚠️ Data not loaded. Please refresh the page.")
