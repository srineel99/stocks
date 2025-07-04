import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
from sklearn.linear_model import LinearRegression
import os, random, numpy as np

# --- IST Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing **{today_str}** — Live charts from 9:00 AM onwards")

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

# --- Calculate slope angle ---
def calculate_angle(df):
    df = df.dropna(subset=["Close"])
    if len(df) < 10:
        return None
    x = np.arange(len(df)).reshape(-1, 1)
    y = df["Close"].values.reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    slope = model.coef_[0][0]
    angle = np.degrees(np.arctan(slope))
    return angle

# --- Trigger download ---
if "intraday_data" not in st.session_state:
    st.info("📥 Downloading intraday data...")
    st.session_state.intraday_data = {}
    bar = st.progress(0)
    random.shuffle(tickers)
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            st.session_state.intraday_data[ticker] = df
        bar.progress((i + 1) / len(tickers))
    st.success("✅ All intraday data downloaded!")

# --- Filter based on angle ---
ascending = []
descending = []
neutral = []

for symbol, df in st.session_state.intraday_data.items():
    angle = calculate_angle(df)
    if angle is None:
        continue
    if 38 <= angle <= 52:
        ascending.append((symbol, df, angle))
    elif -52 <= angle <= -38:
        descending.append((symbol, df, angle))
    else:
        neutral.append((symbol, df, angle))

# --- Plotting ---
def plot_group(title, group_data):
    st.subheader(title)
    for i in range(0, len(group_data), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(group_data):
                break
            symbol, df, angle = group_data[idx]
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            ax.set_title(f"{symbol} (angle={angle:.1f}°)", fontsize=9)
            ax.set_ylabel("Price", fontsize=8)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

# --- Display grouped charts ---
if not st.session_state.intraday_data:
    st.warning("⚠️ No intraday data found.")
else:
    if ascending:
        plot_group("📈 Ascending Charts (≈ +45°)", ascending)
    if descending:
        plot_group("📉 Descending Charts (≈ -45°)", descending)
    if neutral:
        plot_group("➖ Neutral / Other Charts", neutral)
