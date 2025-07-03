import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MinuteLocator
from datetime import datetime, timedelta, timezone
import os
import numpy as np
import random

# ------------------ Timezone Setup ------------------
IST = timezone(timedelta(hours=5, minutes=30))
today_ist = datetime.now(IST).date()
now_ist = datetime.now(IST)

# ------------------ Streamlit Page Config ------------------
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📈 NSE500 Live Charts")
st.markdown(f"📅 Showing: **{today_ist}**")
st.markdown("🔁 Refresh the page to load latest data.")

# ------------------ Load Tickers ------------------
@st.cache_data
def load_tickers(path="data/Charts-data/tickers_Nifty500.txt", count=100):
    if not os.path.exists(path):
        st.error(f"Ticker file not found: {path}")
        return []
    with open(path) as f:
        tickers = [line.strip().upper() + ".NS" for line in f if line.strip()]
    return random.sample(tickers, min(count, len(tickers)))

tickers = load_tickers(count=500)
st.markdown(f"📌 Total Tickers Loaded: `{len(tickers)}`")

# ------------------ Sidebar Filter ------------------
group_filter = st.sidebar.radio(
    "📊 Show Chart Group",
    ["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"],
    index=0,
)

# ------------------ Intraday Fetch Function ------------------
@st.cache_data(ttl=600)
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, auto_adjust=True)
        df = df[df.index >= datetime.combine(today_ist, datetime.strptime("09:00", "%H:%M").time()).replace(tzinfo=IST)]
        return df
    except Exception as e:
        return pd.DataFrame()

# ------------------ Slope Calculation ------------------
def calculate_slope(df):
    if len(df) < 2:
        return None
    y = df["Close"].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    return slope

# ------------------ Categorize Stocks ------------------
def categorize_by_slope(data_dict):
    ascending = {}
    descending = {}
    neutral = {}
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

# ------------------ Load and Categorize Data ------------------
if "live_data" not in st.session_state:
    with st.spinner("📥 Fetching live data..."):
        data_dict = {}
        for i, ticker in enumerate(tickers):
            df = fetch_data(ticker)
            if not df.empty:
                data_dict[ticker] = df
        ascending, descending, neutral = categorize_by_slope(data_dict)
        st.session_state.live_data = {
            "Ascending (≈ +45°)": ascending,
            "Descending (≈ -45°)": descending,
            "Neutral": neutral,
        }
        st.success("✅ Live intraday data loaded and grouped!")

# ------------------ Chart Plotting ------------------
def plot_chart(symbol, df, slope=None):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df.index, df["Close"], linewidth=1)
    title = f"{symbol}" if slope is None else f"{symbol} (slope={slope:.2f})"
    ax.set_title(title, fontsize=10)
    ax.set_ylabel("Price", fontsize=9)
    ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
    plt.tight_layout()
    return fig

# ------------------ Display Filtered Charts ------------------
def display_charts(group_name):
    group_data = st.session_state.live_data.get(group_name, {})
    if not group_data:
        st.warning(f"⚠️ No data available for {group_name}")
        return
    st.markdown(f"### 📈 {group_name} — {len(group_data)} Charts")
    cols = st.columns(2)
    for i, (symbol, (df, slope)) in enumerate(group_data.items()):
        with cols[i % 2]:
            st.pyplot(plot_chart(symbol, df, slope))

# ------------------ Main Chart Display ------------------
if group_filter == "All":
    for grp in ["Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"]:
        display_charts(grp)
else:
    display_charts(group_filter)
