import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator
from datetime import datetime, timedelta, timezone
import numpy as np
import random
import os

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")

st.title("📈 NSE500 Live Charts")
st.markdown(f"📅 **Showing:** `{TODAY}`")
st.markdown("🔄 Refresh the page to load latest data.")

# Sidebar option to filter chart group
chart_group = st.sidebar.radio(
    "📊 Show Chart Group",
    ["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"],
    index=0
)

# Read tickers from file
ticker_path = "data/Charts-data/tickers_Nifty500.txt"
if not os.path.exists(ticker_path):
    st.error("Ticker file not found!")
    st.stop()

with open(ticker_path, "r") as f:
    tickers = [line.strip() for line in f if line.strip()]

st.markdown(f"📌 **Total Tickers Loaded:** `{len(tickers)}`")

@st.cache_data(ttl=3600)
def fetch_intraday_data(symbols, interval="5m", period="1d"):
    data_dict = {}
    for symbol in symbols:
        try:
            df = yf.download(symbol, interval=interval, period=period, progress=False)
            if not df.empty:
                df = df.tz_convert("Asia/Kolkata")
                df = df.between_time("09:15", "15:30")
                df = df[["Close"]].dropna()
                if len(df) > 2:
                    data_dict[symbol] = df.copy()
        except Exception:
            continue
    return data_dict

def calculate_slope(df):
    try:
        y = df["Close"].values
        x = np.arange(len(y))
        if len(x) < 3:
            return None
        slope, _ = np.polyfit(x, y, 1)
        return slope
    except Exception:
        return None

def categorize_by_slope(data_dict):
    ascending, descending, neutral = {}, {}, {}

    for symbol, df in data_dict.items():
        slope = calculate_slope(df)
        if slope is None:
            continue
        if 0.2 <= slope <= 1.5:
            ascending[symbol] = (df, slope)
        elif -1.5 <= slope <= -0.2:
            descending[symbol] = (df, slope)
        else:
            neutral[symbol] = (df, slope)

    return ascending, descending, neutral

def plot_chart(symbol, df, slope=None):
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.plot(df.index, df["Close"], linewidth=1.5)
    ax.set_title(f"{symbol}" + (f" (slope={slope:.2f})" if slope is not None else ""), fontsize=9)
    ax.set_ylabel("Price", fontsize=7)
    ax.tick_params(axis="x", labelsize=6)
    ax.tick_params(axis="y", labelsize=6)
    ax.xaxis.set_major_locator(HourLocator(interval=1))
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig

def display_group(title, chart_dict):
    st.subheader(title)
    if not chart_dict:
        st.warning(f"No data available for {title}")
        return

    symbols = list(chart_dict.keys())
    cols = st.columns(2)
    for idx, symbol in enumerate(symbols):
        df, slope = chart_dict[symbol]
        with cols[idx % 2]:
            st.pyplot(plot_chart(symbol, df, slope))

# Limit to max 500 stocks for better performance (or use all)
selected_tickers = random.sample(tickers, len(tickers))

# Fetch and categorize
with st.status("📡 Fetching live data...", expanded=False):
    data_dict = fetch_intraday_data(selected_tickers)
    ascending, descending, neutral = categorize_by_slope(data_dict)

# Show chart groups based on sidebar filter
if chart_group == "All":
    display_group("📈 Ascending (≈ +45°)", ascending)
    display_group("📉 Descending (≈ -45°)", descending)
    display_group("➖ Neutral", neutral)
elif chart_group == "Ascending (≈ +45°)":
    display_group("📈 Ascending (≈ +45°)", ascending)
elif chart_group == "Descending (≈ -45°)":
    display_group("📉 Descending (≈ -45°)", descending)
else:
    display_group("➖ Neutral", neutral)
