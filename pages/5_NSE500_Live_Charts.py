import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MinuteLocator
from datetime import datetime, timedelta, timezone
import numpy as np
import os
import random

# --- Timezone and cache setup ---
IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()
CACHE_FILE = f"data/Charts-data/live_cache_{TODAY}.pkl"

# --- Load tickers ---
TICKER_FILE = "data/Charts-data/tickers_Nifty500.txt"
with open(TICKER_FILE, "r") as f:
    TICKERS = sorted([line.strip() for line in f if line.strip()])

# --- Streamlit page config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📈 NSE500 Live Charts")
st.markdown(f"📅 **Showing:** `{TODAY}`")
st.info("🔄 Refresh the page to load latest data.")

# --- Sidebar filter ---
group_option = st.sidebar.radio("📂 Show Chart Group", ["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"])

# --- Utilities ---
def is_valid_slope(slope):
    return slope is not None and isinstance(slope, (int, float)) and np.isfinite(slope)

def plot_chart(symbol: str, df: pd.DataFrame, slope=None):
    fig, ax = plt.subplots(figsize=(5, 2))
    ax.plot(df["Datetime"], df["Close"])
    if is_valid_slope(slope):
        ax.set_title(f"{symbol} (slope={slope:.2f})", fontsize=9)
    else:
        ax.set_title(symbol, fontsize=9)
    ax.set_ylabel("Price")
    ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def calculate_slope(df):
    df = df.reset_index(drop=True)
    x = np.arange(len(df))
    y = df["Close"].values
    if len(x) < 2:
        return None
    A = np.vstack([x, np.ones(len(x))]).T
    m, _ = np.linalg.lstsq(A, y, rcond=None)[0]
    return m

@st.cache_data(ttl=600, show_spinner="📥 Downloading live intraday data...")
def download_live_data():
    data = {}
    selected_tickers = random.sample(TICKERS, len(TICKERS))  # full list
    for symbol in selected_tickers:
        try:
            df = yf.download(
                tickers=symbol,
                interval="5m",
                period="1d",
                progress=False
            )
            if df.empty:
                continue
            df = df[df.index.time >= datetime.strptime("09:15", "%H:%M").time()]
            df = df.tz_localize("UTC").tz_convert("Asia/Kolkata")
            df = df.reset_index()[["Datetime", "Close"]]
            data[symbol] = df
        except Exception:
            continue
    return data

# --- Download or Load Cached ---
if os.path.exists(CACHE_FILE):
    live_data = pd.read_pickle(CACHE_FILE)
else:
    live_data = download_live_data()
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    pd.to_pickle(live_data, CACHE_FILE)

st.success(f"📌 Total Tickers Loaded: `{len(live_data)}`")

# --- Grouping by slope ---
ascending = []
descending = []
neutral = []

for symbol, df in live_data.items():
    slope = calculate_slope(df)
    if slope is None:
        neutral.append((symbol, df, None))
    elif 0.20 <= slope <= 0.80:
        ascending.append((symbol, df, slope))
    elif -0.80 <= slope <= -0.20:
        descending.append((symbol, df, slope))
    else:
        neutral.append((symbol, df, slope))

# --- Display Function ---
def display_group(title, group_data):
    if not group_data:
        st.warning(f"⚠️ No data available for {title}")
        return
    st.markdown(f"### {title}")
    for i in range(0, len(group_data), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(group_data):
                symbol, df, slope = group_data[i + j]
                cols[j].pyplot(plot_chart(symbol, df, slope))

# --- Render charts by filter ---
if group_option == "All":
    display_group("📈 Ascending (≈ +45°)", ascending)
    display_group("📉 Descending (≈ -45°)", descending)
    display_group("➖ Neutral", neutral)
elif "Ascending" in group_option:
    display_group("📈 Ascending (≈ +45°)", ascending)
elif "Descending" in group_option:
    display_group("📉 Descending (≈ -45°)", descending)
elif "Neutral" in group_option:
    display_group("➖ Neutral", neutral)
