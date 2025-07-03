import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, time, timedelta, timezone
import os
import time as systime

# -------------------- Timezone Setup (IST) --------------------
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# -------------------- Page Config --------------------
st.set_page_config(page_title="NSE500 Intraday Charts", layout="wide")
st.title("📈 Intraday Charts — From 9:15 AM IST (Nifty 500)")
st.markdown(f"📅 **Showing {today_str} | 5-minute Interval Data**")

# -------------------- Load Tickers --------------------
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
st.markdown(f"📊 **Total Tickers:** {len(tickers)}")

# -------------------- Fetch Intraday Data --------------------
def fetch_intraday_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.index = df.index.tz_convert(IST)
        start_time = datetime.combine(now_ist.date(), time(9, 15)).replace(tzinfo=IST)
        return df[df.index >= start_time]
    except Exception:
        return pd.DataFrame()

# -------------------- Classify Trend --------------------
def classify_trend(df, threshold=0.05):
    if df is None or df.empty:
        return "flat", 0
    y = df["Close"].values
    slope = (y[-1] - y[0]) / len(y)
    if slope > threshold:
        return "ascending", slope
    elif slope < -threshold:
        return "descending", slope
    else:
        return "flat", slope

# -------------------- Fetch and Classify --------------------
available_data = {"ascending": [], "descending": [], "flat": []}
progress = st.progress(0, text="⏳ Fetching and classifying live intraday charts...")

for i, ticker in enumerate(tickers):
    df = fetch_intraday_data(ticker)
    trend, slope = classify_trend(df)
    if not df.empty:
        available_data[trend].append((ticker, df, slope))
    systime.sleep(0.8)
    progress.progress((i + 1) / len(tickers))
progress.empty()

# -------------------- Display Charts Grouped by Trend --------------------
def plot_chart(symbol, df, slope):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df.index, df["Close"], lw=1.2)
    ax.set_title(f"{symbol} (slope={slope:.2f})", fontsize=10)
    ax.set_ylabel("Close", fontsize=8)
    ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
    plt.tight_layout()
    return fig

def display_group(title, group_data):
    st.subheader(title)
    for i in range(0, len(group_data), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(group_data):
                break
            symbol, df, slope = group_data[idx]
            cols[j].pyplot(plot_chart(symbol, df, slope))

if not any(available_data.values()):
    st.warning("⚠️ No intraday data available for any stock. Try again later.")
else:
    st.success("✅ Live intraday data loaded and sorted by trend!")
    display_group("📈 Ascending (≈ +45°) Charts", available_data["ascending"])
    display_group("📉 Descending (≈ -45°) Charts", available_data["descending"])
    display_group("➡️ Flat/Other Charts", available_data["flat"])
