import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator
from datetime import datetime, timedelta, timezone
import os
import random
import numpy as np

# --- Config & Constants ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📈 NSE500 Live Charts")

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()
st.markdown(f"📅 **Showing:** {TODAY}")
st.info("🔄 Refresh the page to load latest data.")

TICKER_FILE = "data/Charts-data/tickers_Nifty500.txt"

# --- Sidebar Filter ---
st.sidebar.divider()
chart_group = st.sidebar.radio(
    "🗂️ Show Chart Group",
    ["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"],
    index=0
)

# --- Load Tickers ---
@st.cache_data(ttl=600)
def load_tickers():
    with open(TICKER_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

tickers = load_tickers()
st.markdown(f"📌 **Total Tickers Loaded:** `{len(tickers)}`")

# --- Download & Cache Intraday Data ---
@st.cache_data(ttl=600)
def fetch_intraday_data(ticker):
    try:
        df = yf.download(ticker, interval="5m", period="1d", progress=False)
        if df.empty or "Close" not in df.columns:
            return None
        df = df.tz_convert("Asia/Kolkata")
        df = df[df.index.time >= datetime.strptime("09:15", "%H:%M").time()]
        return df
    except Exception:
        return None

# --- Calculate Slope ---
def compute_slope(df):
    try:
        y = df["Close"].values
        x = np.arange(len(y))
        slope = np.polyfit(x, y, 1)[0]
        return slope
    except Exception:
        return None

# --- Plot Chart ---
def plot_chart(symbol, df, slope=None):
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.plot(df.index, df["Close"], linewidth=1.5)
    title = f"{symbol}"
    if isinstance(slope, (int, float)):
        title += f" (slope={slope:.2f})"
    ax.set_title(title, fontsize=9)
    ax.set_ylabel("Price", fontsize=7)
    ax.tick_params(axis="x", labelsize=6)
    ax.tick_params(axis="y", labelsize=6)
    ax.xaxis.set_major_locator(HourLocator(interval=1))
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig

# --- Display Charts by Group ---
def display_group(label, group_data):
    st.subheader(label)
    if not group_data:
        st.warning(f"⚠️ No data available for {label}")
        return
    cols = st.columns(2)
    for i, (symbol, df, slope) in enumerate(group_data):
        with cols[i % 2]:
            st.pyplot(plot_chart(symbol, df, slope))

# --- Main Logic ---
ascending, descending, neutral = [], [], []
for ticker in tickers:
    df = fetch_intraday_data(ticker)
    if df is None or df.empty:
        continue
    slope = compute_slope(df)
    if slope is not None:
        if 0.2 < slope < 2:
            ascending.append((ticker, df, slope))
        elif -2 < slope < -0.2:
            descending.append((ticker, df, slope))
        else:
            neutral.append((ticker, df, slope))
    else:
        neutral.append((ticker, df, None))

# --- Filter & Display ---
if chart_group == "Ascending (≈ +45°)":
    display_group("📈 Ascending (≈ +45°)", ascending)
elif chart_group == "Descending (≈ -45°)":
    display_group("📉 Descending (≈ -45°)", descending)
elif chart_group == "Neutral":
    display_group("➖ Neutral", neutral)
else:
    display_group("📈 Ascending (≈ +45°)", ascending)
    display_group("📉 Descending (≈ -45°)", descending)
    display_group("➖ Neutral", neutral)
