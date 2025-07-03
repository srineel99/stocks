import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
from sklearn.linear_model import LinearRegression
import os
import random
import numpy as np

# --- IST Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📈 NSE500 Live Charts")
st.markdown(f"📅 Showing: **{today_str}**")
st.info("🔄 Refresh the page to load latest data.")

# --- Load tickers ---
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
st.markdown(f"📌 **Total Tickers Loaded:** `{len(tickers)}`")

# --- Fetch intraday data ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        df = df.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except:
        return pd.DataFrame()

def calculate_slope_deg(prices: pd.Series):
    if len(prices) < 10:
        return None
    x = np.arange(len(prices)).reshape(-1, 1)
    y = prices.values.reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    slope = model.coef_[0][0]
    degrees = np.degrees(np.arctan(slope))
    return degrees

# --- Data loading ---
if "intraday_data" not in st.session_state:
    st.session_state.intraday_data = {}
    bar = st.progress(0)
    random.shuffle(tickers)
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            st.session_state.intraday_data[ticker] = df
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Intraday data downloaded and grouped!")

# --- Categorize charts ---
ascending, descending, neutral = [], [], []
for symbol, df in st.session_state.intraday_data.items():
    slope_deg = calculate_slope_deg(df["Close"])
    if slope_deg is None:
        continue
    if 35 <= slope_deg <= 55:
        ascending.append((symbol, df, slope_deg))
    elif -55 <= slope_deg <= -35:
        descending.append((symbol, df, slope_deg))
    else:
        neutral.append((symbol, df, slope_deg))

# --- Chart plotting ---
def display_group(title, group):
    if not group:
        st.warning(f"⚠️ No data available for {title}")
        return
    st.subheader(title)
    for i in range(0, len(group), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j >= len(group):
                break
            symbol, df, slope_deg = group[i + j]
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            ax.set_title(f"{symbol} (slope={slope_deg:.1f}°)", fontsize=9)
            ax.set_ylabel("Price", fontsize=8)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

# --- Display in grouped order ---
display_group("📈 Ascending (≈ +45°)", ascending)
display_group("📉 Descending (≈ -45°)", descending)
display_group("📊 Neutral", neutral)
