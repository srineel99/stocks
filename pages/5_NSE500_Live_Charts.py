import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
import os
import random

# --- Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Page config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts with ~45° Trend Detection")
st.markdown(f"📅 Showing **{today_str}** intraday data (from 9:00 AM IST)")

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
st.markdown(f"📈 **Tickers Loaded:** {len(tickers)}")

# --- Download intraday data ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        df = df.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except:
        return pd.DataFrame()

# --- Classify trend using relaxed slope logic ---
def classify_trend(df):
    if df is None or df.empty or "Close" not in df.columns:
        return "other", 0.0
    y = df["Close"].values
    if len(y) < 2:
        return "other", 0.0
    slope = (y[-1] - y[0]) / len(y)
    if slope > 0.15:
        return "ascending", slope
    elif slope < -0.15:
        return "descending", slope
    else:
        return "other", slope

# --- Session: Download all data and classify ---
if "classified_data" not in st.session_state:
    st.info("📥 Downloading intraday data...")
    bar = st.progress(0)

    ascending, descending, other = [], [], []
    random.shuffle(tickers)
    for i, symbol in enumerate(tickers):
        df = fetch_intraday(symbol)
        trend, slope = classify_trend(df)
        if not df.empty:
            if trend == "ascending":
                ascending.append((symbol, df, slope))
            elif trend == "descending":
                descending.append((symbol, df, slope))
            else:
                other.append((symbol, df, slope))
        bar.progress((i + 1) / len(tickers))

    st.session_state.classified_data = {
        "ascending": ascending,
        "descending": descending,
        "other": other
    }
    st.success("✅ Data loaded and categorized!")

data = st.session_state.get("classified_data", {})
asc = data.get("ascending", [])
desc = data.get("descending", [])
oth = data.get("other", [])

st.markdown(f"📊 **Ascending:** {len(asc)} | 📉 Descending:** {len(desc)} | ➡️ Other:** {len(oth)}")

# --- Chart plot function ---
def plot_group(title, group_data):
    st.subheader(title)
    if not group_data:
        st.warning(f"⚠️ No charts found for {title}")
        return
    for i in range(0, len(group_data), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(group_data):
                break
            symbol, df, slope = group_data[idx]
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1.2)
            ax.set_title(f"{symbol} (slope={slope:.2f})", fontsize=10)
            ax.set_ylabel("Price", fontsize=9)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

# --- Display all groups ---
plot_group("📈 Ascending Charts (≈ +45°)", asc)
plot_group("📉 Descending Charts (≈ -45°)", desc)
plot_group("➡️ Other Charts", oth)
