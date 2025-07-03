import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MinuteLocator
import numpy as np
from datetime import datetime, timedelta, timezone
import os

# --- Timezone & Config ---
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()

st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.markdown("## 📈 NSE500 Live Charts")
st.markdown(f"📅 **Showing:** `{TODAY}`")
st.info("🔄 Refresh the page to load latest data.")

# --- Load tickers ---
ticker_path = "data/Charts-data/tickers_Nifty500.txt"
with open(ticker_path, "r") as f:
    tickers = sorted([line.strip() for line in f if line.strip()])

st.markdown(f"📌 **Total Tickers Loaded:** `{len(tickers)}`")

# --- Sidebar filter ---
st.sidebar.markdown("### 🗂️ Show Chart Group")
chart_group = st.sidebar.radio("Filter charts by trend", options=["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"])

# --- Cache: Intraday Data Downloader ---
@st.cache_data(ttl=60 * 30)
def download_intraday(symbol):
    try:
        df = yf.download(
            tickers=symbol,
            interval="1m",
            period="1d",
            progress=False,
            threads=True,
        )
        if df.empty or "Close" not in df.columns:
            return None

        df = df.tz_localize("UTC").tz_convert("Asia/Kolkata")
        df = df[df.index.time >= datetime.strptime("09:00", "%H:%M").time()]
        df = df[["Close"]].rename(columns={"Close": "Price"})
        return df
    except:
        return None

# --- Slope Calculation ---
def calculate_slope(df):
    y = df["Price"].values
    x = np.arange(len(y))
    if len(x) < 2:
        return None
    slope, _ = np.polyfit(x, y, 1)
    return slope

# --- Chart Plotter ---
def plot_chart(symbol, df, slope=None):
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.plot(df.index, df["Price"], linewidth=1)
    if slope is not None and not np.isnan(slope):
        ax.set_title(f"{symbol} (slope={slope:.2f})", fontsize=9)
    else:
        ax.set_title(f"{symbol}", fontsize=9)
    ax.set_ylabel("Price", fontsize=8)
    ax.tick_params(axis="x", labelsize=6, rotation=45)
    ax.tick_params(axis="y", labelsize=7)
    ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
    fig.tight_layout()
    return fig

# --- Display grouped charts ---
def display_group(title, group_data):
    st.markdown(f"### {title}")
    if not group_data:
        st.warning(f"No data available for {title}")
        return
    cols = st.columns(2)
    for i, (symbol, df, slope) in enumerate(group_data):
        with cols[i % 2]:
            st.pyplot(plot_chart(symbol, df, slope))

# --- Main Data Loading ---
ascending = []
descending = []
neutral = []
all_loaded = []

with st.spinner("📡 Downloading live intraday data..."):
    for symbol in tickers:
        df = download_intraday(symbol)
        if df is None or df.empty:
            continue
        slope = calculate_slope(df)
        all_loaded.append((symbol, df, slope))

        if slope is None or np.isnan(slope):
            neutral.append((symbol, df, slope))
        elif 0.3 <= slope <= 1.5:
            ascending.append((symbol, df, slope))
        elif -1.5 <= slope <= -0.3:
            descending.append((symbol, df, slope))
        else:
            neutral.append((symbol, df, slope))

# --- Chart Display Based on Sidebar Filter ---
if chart_group == "All":
    display_group("📈 Ascending (≈ +45°)", ascending)
    display_group("📉 Descending (≈ -45°)", descending)
    display_group("📊 Neutral", neutral)
elif chart_group == "Ascending (≈ +45°)":
    display_group("📈 Ascending (≈ +45°)", ascending)
elif chart_group == "Descending (≈ -45°)":
    display_group("📉 Descending (≈ -45°)", descending)
elif chart_group == "Neutral":
    display_group("📊 Neutral", neutral)
