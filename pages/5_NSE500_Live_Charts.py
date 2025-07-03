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

# --- Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Page Setup ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing **{today_str}** — From first tick after 9:00 AM IST")

# --- Load Tickers ---
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

# --- Fetch Intraday Data ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        if df.empty or "Close" not in df.columns:
            return pd.DataFrame()
        df = df.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df[["Close"]].dropna()
    except:
        return pd.DataFrame()

# --- Calculate Angle of Trend ---
def calculate_angle(df):
    if df is None or df.empty or len(df) < 2:
        return None
    y = df["Close"].values
    x = np.arange(len(y)).reshape(-1, 1)
    y_norm = (y - y.min()) / (y.max() - y.min() + 1e-9)
    model = LinearRegression().fit(x, y_norm)
    slope = model.coef_[0]
    angle = np.degrees(np.arctan(slope))
    return angle

# --- Trigger Data Fetch ---
if "intraday_data" not in st.session_state:
    st.info("📥 Fetching intraday data...")
    st.session_state.intraday_data = {}
    random.shuffle(tickers)
    bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            st.session_state.intraday_data[ticker] = df
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Live intraday data loaded!")

# --- Group by Trend Angle ---
ascending, descending, others = [], [], []

for symbol, df in st.session_state.intraday_data.items():
    angle = calculate_angle(df)
    if angle is None:
        continue
    if 30 <= angle <= 60:
        ascending.append((symbol, df, angle))
    elif -60 <= angle <= -30:
        descending.append((symbol, df, angle))
    else:
        others.append((symbol, df, angle))

# --- Plotting Function ---
def plot_group(title, data_group):
    st.subheader(title)
    for i in range(0, len(data_group), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(data_group):
                break
            symbol, df, angle = data_group[idx]
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            ax.set_title(f"{symbol} (∠={angle:.1f}°)", fontsize=10)
            ax.set_ylabel("Price", fontsize=9)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

# --- Display Charts ---
if st.session_state.intraday_data:
    plot_group("📈 Ascending Charts (≈ +45°)", ascending)
    plot_group("📉 Descending Charts (≈ -45°)", descending)
    plot_group("➡️ Others", others)
else:
    st.warning("⚠️ No intraday data found. Please refresh.")
