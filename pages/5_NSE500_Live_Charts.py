import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta, time, timezone
import os

# --- Timezone: IST ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.strftime("%Y-%m-%d")

# --- Page Config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts with ~45° Trend Detection")
st.markdown(f"📅 Showing **{today_str}** intraday data (from 9:00 AM IST)")
st.markdown("🔄 Refresh the page for latest data")

# --- Load Tickers ---
@st.cache_data
def load_tickers():
    path = "data/Charts-data/tickers_Nifty500.txt"
    if not os.path.exists(path):
        st.error("❌ Ticker file not found.")
        return []
    with open(path) as f:
        return [
            line.strip().upper() if line.strip().upper().endswith(".NS")
            else line.strip().upper() + ".NS"
            for line in f if line.strip()
        ]

tickers = load_tickers()
st.markdown(f"📈 **Tickers Loaded:** {len(tickers)}")

# --- Download intraday data (cached) ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        if df.empty or "Close" not in df.columns:
            return pd.DataFrame()
        df = df.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), time(9, 0))]
        return df.dropna(subset=["Close"])
    except:
        return pd.DataFrame()

# --- Calculate slope angle ---
def calculate_angle(df):
    if df.empty or len(df) < 10:
        return None
    y = df["Close"].values.reshape(-1, 1)
    x = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    slope = model.coef_[0][0]
    angle_rad = np.arctan(slope)
    return np.degrees(angle_rad)

# --- Classify by angle ---
def classify(df):
    angle = calculate_angle(df)
    if angle is None:
        return "other", angle
    if 35 <= angle <= 55:
        return "ascending", angle
    elif -55 <= angle <= -35:
        return "descending", angle
    else:
        return "other", angle

# --- Download and process all tickers ---
if "intraday_data" not in st.session_state:
    st.session_state.intraday_data = {"ascending": [], "descending": [], "other": []}
    bar = st.progress(0, text="📡 Fetching intraday data...")

    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            trend, angle = classify(df)
            st.session_state.intraday_data[trend].append((ticker, df, angle))
        bar.progress((i + 1) / len(tickers))
    bar.empty()
    st.success("✅ Data loaded and categorized!")

# --- Chart Plotting ---
def plot_chart(ticker, df, angle):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df.index, df["Close"], lw=1.2)
    label = f"{ticker} ({angle:.1f}°)" if angle is not None else ticker
    ax.set_title(label, fontsize=10)
    ax.set_ylabel("Price", fontsize=8)
    ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
    plt.tight_layout()
    return fig

# --- Display grouped charts ---
def display_group(title, group_data):
    if not group_data:
        return
    st.subheader(title)
    for i in range(0, len(group_data), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(group_data):
                ticker, df, angle = group_data[i + j]
                cols[j].pyplot(plot_chart(ticker, df, angle))

# --- Final Chart Display ---
data = st.session_state.intraday_data
display_group("📈 Ascending Charts (≈ +45°)", data["ascending"])
display_group("📉 Descending Charts (≈ -45°)", data["descending"])
display_group("➡️ Other Charts", data["other"])
