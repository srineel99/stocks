import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
from sklearn.linear_model import LinearRegression
import os, random

# --- IST Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Page config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing **{today_str}** data — Starting from first available tick after 9:00 AM IST")

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

# --- Download intraday data (cached) ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        df = df.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except:
        return pd.DataFrame()

# --- Angle-based trend detection ---
def get_trend_angle(df):
    try:
        y = df["Close"].values.reshape(-1, 1)
        x = np.arange(len(y)).reshape(-1, 1)
        model = LinearRegression().fit(x, y)
        slope = model.coef_[0][0]
        angle_deg = np.degrees(np.arctan(slope))
        return angle_deg
    except:
        return None

# --- Trigger Download ---
if "intraday_data" not in st.session_state:
    st.info("📥 Fetching live intraday data (1m interval)...")
    st.session_state.intraday_data = {"ascending": [], "descending": [], "flat": []}
    bar = st.progress(0)
    random.shuffle(tickers)
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            angle = get_trend_angle(df)
            if angle is not None:
                if 40 <= angle <= 50:
                    st.session_state.intraday_data["ascending"].append((ticker, df, angle))
                elif -50 <= angle <= -40:
                    st.session_state.intraday_data["descending"].append((ticker, df, angle))
                else:
                    st.session_state.intraday_data["flat"].append((ticker, df, angle))
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Live intraday data loaded and classified!")

# --- Plot grouped charts ---
def plot_group(title, group):
    st.subheader(title)
    for i in range(0, len(group), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j >= len(group): break
            symbol, df, angle = group[i + j]
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            ax.set_title(f"{symbol} (angle={angle:.1f}°)", fontsize=10)
            ax.set_ylabel("Price", fontsize=9)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

# --- Display all charts ---
if st.session_state.intraday_data:
    data = st.session_state.intraday_data
    if data["ascending"]:
        plot_group("📈 Ascending (≈ +45°)", data["ascending"])
    if data["descending"]:
        plot_group("📉 Descending (≈ -45°)", data["descending"])
    if data["flat"]:
        plot_group("🔄 Flat/Other", data["flat"])
else:
    st.warning("⚠️ No data loaded. Please refresh the page.")
