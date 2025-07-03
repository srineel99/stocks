import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
from sklearn.linear_model import LinearRegression
import numpy as np
import os
import random

# --- IST Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Page config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing **{today_str}** data — From 9:00 AM IST onwards")

# --- Load tickers from file ---
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
st.markdown(f"📈 **Total Tickers:** {len(tickers)}")

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

# --- Calculate slope angle using linear regression ---
def calculate_angle(df):
    if df is None or df.empty or len(df) < 2:
        return None
    df = df.dropna(subset=["Close"])
    if df.empty:
        return None
    y = df["Close"].values
    x = np.arange(len(y)).reshape(-1, 1)
    y = y.reshape(-1, 1)
    try:
        model = LinearRegression().fit(x, y)
        slope = model.coef_[0][0]
        angle_rad = np.arctan(slope)
        angle_deg = np.degrees(angle_rad)
        return angle_deg
    except:
        return None

# --- Trigger data download ---
if "intraday_data" not in st.session_state:
    st.info("📥 Fetching live intraday data (1m interval)...")
    st.session_state.intraday_data = []
    bar = st.progress(0)
    random.shuffle(tickers)
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            angle = calculate_angle(df)
            st.session_state.intraday_data.append((ticker, df, angle))
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Data loaded.")

# --- Group based on angle ---
ascending = []
descending = []
flat = []

for symbol, df, angle in st.session_state.intraday_data:
    if angle is None:
        flat.append((symbol, df, angle))
    elif 35 <= angle <= 55:
        ascending.append((symbol, df, angle))
    elif -55 <= angle <= -35:
        descending.append((symbol, df, angle))
    else:
        flat.append((symbol, df, angle))

# --- Plotting function ---
def plot_group(title, group):
    if not group:
        return
    st.subheader(title)
    for i in range(0, len(group), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j >= len(group):
                break
            symbol, df, angle = group[i + j]
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            angle_label = f"{angle:.1f}°" if isinstance(angle, (int, float)) and np.isfinite(angle) else "N/A"
            ax.set_title(f"{symbol} (angle={angle_label})", fontsize=10)
            ax.set_ylabel("Price", fontsize=9)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

# --- Display Groups ---
if st.session_state.intraday_data:
    plot_group("📈 Ascending Charts (≈ +45°)", ascending)
    plot_group("📉 Descending Charts (≈ -45°)", descending)
    plot_group("➡️ Flat/Other Charts", flat)
else:
    st.warning("⚠️ No valid data available.")
