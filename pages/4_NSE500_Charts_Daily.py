import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, time, timedelta, timezone
import os

# -------------------- Timezone Setup --------------------
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# -------------------- Streamlit Config --------------------
st.set_page_config(page_title="Intraday Charts", layout="wide")
st.title("📈 Intraday Charts — From 9:15 AM IST (Nifty 500)")
st.markdown(f"📅 **Showing: {today_str}**")

# -------------------- Load Tickers --------------------
@st.cache_data
def load_tickers():
    path = "data/Charts-data/tickers_Nifty500.txt"  # ✅ make sure this path is correct
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
st.markdown(f"🧾 Total Tickers: **{len(tickers)}**")

# -------------------- Download Intraday Data --------------------
def fetch_intraday_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
        df = df[df.index >= datetime.combine(now_ist.date(), time(9, 15)).replace(tzinfo=IST)]
        return df
    except:
        return pd.DataFrame()

st.info("🔄 Fetching fresh intraday data (5m interval)...")
available_data = {}
for ticker in tickers:
    df = fetch_intraday_data(ticker)
    if not df.empty:
        available_data[ticker] = df

if not available_data:
    st.warning("⚠️ No intraday data available for any stock. Try again later.")
else:
    st.success("✅ Live intraday data loaded!")

    for i, (symbol, df) in enumerate(available_data.items()):
        if i % 2 == 0:
            cols = st.columns(2)

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(df.index, df["Close"], lw=1)
        ax.set_title(symbol, fontsize=11)
        ax.set_ylabel("Close", fontsize=9)
        ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
        plt.tight_layout()
        cols[i % 2].pyplot(fig)
        plt.close(fig)
