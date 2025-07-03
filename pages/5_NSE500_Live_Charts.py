import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MinuteLocator
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# --- Page Settings ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.markdown("<h1 style='font-size: 36px;'>📈 NSE500 Live Charts</h1>", unsafe_allow_html=True)

IST = timezone(timedelta(hours=5, minutes=30))
today = datetime.now(IST).date()

# --- Load Tickers ---
with open("data/Charts-data/tickers_Nifty500.txt") as f:
    tickers = [line.strip() for line in f if line.strip()]

st.markdown(f"📅 <b>Showing:</b> {today}", unsafe_allow_html=True)
st.markdown("🔄 Refresh the page to load latest data.")
st.markdown(f"📌 <b>Total Tickers Loaded:</b> <code>{len(tickers)}</code>", unsafe_allow_html=True)

# --- Sidebar Filter ---
st.sidebar.markdown("📂 **Show Chart Group**")
chart_group = st.sidebar.radio(
    "", ["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"],
    index=0,
)

# --- Caching Data ---
@st.cache_data(ttl=300)
def fetch_intraday_data(ticker: str):
    try:
        df = yf.download(ticker, interval="1m", period="1d", progress=False)
        if df.empty or "Close" not in df:
            return None
        df = df.tz_localize(None)
        df = df[df.index.time >= datetime.strptime("09:00", "%H:%M").time()]
        df = df[['Close']].copy()
        df.reset_index(inplace=True)
        df.rename(columns={"index": "Datetime"}, inplace=True)
        return df
    except Exception:
        return None

def compute_slope(df: pd.DataFrame):
    try:
        x = np.arange(len(df))
        y = df["Close"].values
        if len(x) < 2:
            return None
        slope, _ = np.polyfit(x, y, 1)
        return slope
    except Exception:
        return None

def is_valid_slope(slope):
    return slope is not None and np.isfinite(slope)

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

def display_group(label: str, data: list):
    if not data:
        st.warning(f"⚠️ No data available for {label}")
        return
    st.markdown(f"### {label}")
    cols = st.columns(2)
    for idx, (symbol, df, slope) in enumerate(data):
        with cols[idx % 2]:
            st.pyplot(plot_chart(symbol, df, slope))

# --- Fetching & Categorizing ---
with st.spinner("📡 Fetching live intraday data..."):
    ascending, descending, neutral = [], [], []
    for ticker in tickers:
        df = fetch_intraday_data(ticker)
        if df is None or df.empty:
            continue
        slope = compute_slope(df)
        if is_valid_slope(slope):
            if 0.2 < slope < 2:
                ascending.append((ticker, df, slope))
            elif -2 < slope < -0.2:
                descending.append((ticker, df, slope))
            else:
                neutral.append((ticker, df, slope))
        else:
            neutral.append((ticker, df, None))

# --- Display ---
if not any([ascending, descending, neutral]):
    st.warning("⚠️ No intraday chart data available yet. Try refreshing the page after a few minutes.")
else:
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
