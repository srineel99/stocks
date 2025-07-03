import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime, timedelta, timezone
from matplotlib.dates import DateFormatter

# ---------- Setup ----------
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📈 NSE500 Live Charts")

IST = timezone(timedelta(hours=5, minutes=30))
today = datetime.now(IST).date()
st.markdown(f"📅 **Showing:** `{today}`")

# ---------- Cache File ----------
CACHE_FILE = f"data/cache/live_data_{today}.pkl"

# ---------- Load Tickers ----------
TICKER_FILE = "data/Charts-data/tickers_Nifty500.txt"
with open(TICKER_FILE) as f:
    tickers = [line.strip() for line in f if line.strip()]
st.markdown(f"📌 **Total Tickers Loaded:** `{len(tickers)}`")

# ---------- Sidebar Group Selection ----------
st.sidebar.markdown("### 🗂️ Show Chart Group")
chart_group = st.sidebar.radio(
    "Group by trend angle:",
    options=["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"],
    index=0
)

# ---------- Data Downloader ----------
@st.cache_data(ttl=600)
def fetch_intraday_data(symbol):
    try:
        df = yf.download(symbol, interval="1m", period="1d", progress=False)
        df = df[df.index >= df.index[0]]  # Keep as-is from earliest
        df = df[~df.index.duplicated(keep='first')]
        return df[["Close"]].rename(columns={"Close": "Price"})
    except Exception:
        return None

def download_live_data():
    data = {}
    for symbol in tickers:
        df = fetch_intraday_data(symbol)
        if df is not None and not df.empty:
            data[symbol] = df
    return data

# ---------- Load from cache or fetch ----------
if os.path.exists(CACHE_FILE):
    try:
        live_data = pd.read_pickle(CACHE_FILE)
        if not live_data:
            raise ValueError("Empty cache file")
    except Exception:
        st.warning("⚠️ Cache file is empty or broken. Re-downloading...")
        live_data = download_live_data()
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        pd.to_pickle(live_data, CACHE_FILE)
else:
    live_data = download_live_data()
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    pd.to_pickle(live_data, CACHE_FILE)

# ---------- Optional: Force Refresh ----------
if st.button("♻️ Refresh the page to load latest data."):
    live_data = download_live_data()
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    pd.to_pickle(live_data, CACHE_FILE)
    st.experimental_rerun()

if not live_data:
    st.warning("⚠️ No intraday data available. Please try again later.")
    st.stop()

# ---------- Slope Calculation ----------
def calculate_slope(df):
    y = df["Price"].values
    x = np.arange(len(y))
    if len(x) < 2:
        return None
    slope, _ = np.polyfit(x, y, 1)
    return slope

# ---------- Chart Plotter ----------
def plot_chart(symbol, df, slope=None):
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.plot(df.index, df["Price"], linewidth=1)
    ax.set_title(f"{symbol}" + (f" (slope={slope:.2f})" if slope else ""), fontsize=9)
    ax.set_ylabel("Price", fontsize=8)
    ax.tick_params(axis='x', labelsize=6, rotation=45)
    ax.tick_params(axis='y', labelsize=7)
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
    fig.tight_layout()
    return fig

# ---------- Grouping ----------
ascending, descending, neutral = [], [], []
for symbol, df in live_data.items():
    slope = calculate_slope(df)
    if slope is None:
        continue
    if 0.2 <= slope <= 0.8:
        ascending.append((symbol, df, slope))
    elif -0.8 <= slope <= -0.2:
        descending.append((symbol, df, slope))
    else:
        neutral.append((symbol, df, slope))

# ---------- Display Charts ----------
def display_group(title, group):
    if not group:
        st.warning(f"⚠️ No data available for {title}")
        return
    st.markdown(f"### {title}")
    cols = st.columns(2)
    for i, (symbol, df, slope) in enumerate(group):
        with cols[i % 2]:
            st.pyplot(plot_chart(symbol, df, slope))

# ---------- Render Based on Selection ----------
if chart_group == "All":
    display_group("📈 Ascending (≈ +45°)", ascending)
    display_group("📉 Descending (≈ -45°)", descending)
    display_group("🟣 Neutral", neutral)
elif chart_group == "Ascending (≈ +45°)":
    display_group("📈 Ascending (≈ +45°)", ascending)
elif chart_group == "Descending (≈ -45°)":
    display_group("📉 Descending (≈ -45°)", descending)
elif chart_group == "Neutral":
    display_group("🟣 Neutral", neutral)
