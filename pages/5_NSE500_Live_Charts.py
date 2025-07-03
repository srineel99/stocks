import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
from sklearn.linear_model import LinearRegression
import numpy as np
import os, random

# --- Timezone setup for IST ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Streamlit Config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing: **{today_str}** (Live data from 9:00 AM IST)")
st.markdown("🔄 **Refresh the page** to load latest data.")

# --- Load tickers ---
@st.cache_data
def load_tickers():
    path = "data/Charts-data/tickers_Nifty500.txt"
    if not os.path.exists(path):
        st.error(f"Ticker file not found: {path}")
        return []
    with open(path) as f:
        return [line.strip().upper() + ".NS" if not line.strip().upper().endswith(".NS") else line.strip().upper()
                for line in f if line.strip()]

tickers = load_tickers()
st.markdown(f"📈 **Total Tickers Loaded:** {len(tickers)}")

# --- Download intraday data ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        if df.empty or "Close" not in df.columns:
            return pd.DataFrame()
        df = df[["Close"]].dropna()
        df.index = df.index.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except:
        return pd.DataFrame()

# --- Angle calculation using LinearRegression ---
def calculate_angle(df):
    try:
        df = df[["Close"]].dropna()
        y = df["Close"].values
        x = np.arange(len(y)).reshape(-1, 1)
        y = y.reshape(-1, 1)
        model = LinearRegression().fit(x, y)
        slope = model.coef_[0][0]
        angle = np.degrees(np.arctan(slope))
        return angle
    except:
        return None

# --- Download all ticker data and classify ---
if "intraday_data" not in st.session_state:
    st.session_state.intraday_data = {}
    st.info("📥 Downloading intraday data...")
    bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            st.session_state.intraday_data[ticker] = df
        bar.progress((i + 1) / len(tickers))
    st.success("✅ All intraday data downloaded!")

# --- Sort tickers by angle ---
ascending, descending, others = [], [], []
for symbol, df in st.session_state.intraday_data.items():
    angle = calculate_angle(df)
    if angle is None:
        others.append((symbol, df, None))
    elif 30 <= angle <= 60:
        ascending.append((symbol, df, angle))
    elif -60 <= angle <= -30:
        descending.append((symbol, df, angle))
    else:
        others.append((symbol, df, angle))

# --- Chart rendering ---
def plot_group(title, group_data):
    st.subheader(title)
    for i in range(0, len(group_data), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j >= len(group_data):
                break
            symbol, df, angle = group_data[i + j]
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            angle_label = f"{angle:.1f}°" if angle is not None and np.isfinite(angle) else "N/A"
            ax.set_title(f"{symbol} (angle={angle_label})", fontsize=10)
            ax.set_ylabel("Price", fontsize=9)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

# --- Final Display ---
if st.session_state.intraday_data:
    plot_group("📈 Ascending Charts (≈ +45°)", ascending)
    plot_group("📉 Descending Charts (≈ -45°)", descending)
    plot_group("➡️ Other Charts", others)
else:
    st.warning("⚠️ No intraday data found.")
