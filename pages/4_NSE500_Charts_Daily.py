import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, time, timedelta, timezone
import os

# -------------------- Timezone Setup (IST) --------------------
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# -------------------- Config --------------------
st.set_page_config(page_title="NSE500 Charts Daily", layout="wide")
st.title("📊 Intraday Charts — From 9:15 AM IST (Nifty 500)")
st.markdown(f"📅 **Showing {today_str} Data From 9:15 AM IST**")

# -------------------- Load Tickers --------------------
@st.cache_data
def load_tickers():
    path = "data/Charts-data/tickers_Nifty500.txt"  # ✅ FIXED typo from "Nitfy" to "Nifty"
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
st.markdown(f"🧾 **Total Tickers:** {len(tickers)}")

# -------------------- Sidebar Filters --------------------
st.sidebar.header("🔍 Options")
interval = st.sidebar.selectbox("Select Interval", ["1m", "2m", "5m", "10m", "15m"], index=2)
show_all = st.sidebar.checkbox("✅ Show All Charts", value=True)

# -------------------- Fetch Function --------------------
@st.cache_data(ttl=600)
def fetch_intraday_data(ticker, interval):
    try:
        df = yf.download(ticker, period="1d", interval=interval, progress=False, auto_adjust=True)
        start_time = datetime.combine(now_ist.date(), time(9, 15)).replace(tzinfo=IST)
        return df[df.index >= start_time]
    except:
        return pd.DataFrame()

# -------------------- Data Fetch Trigger --------------------
if st.button(f"📥 Load {interval} Intraday Data"):
    st.session_state.data = {}
    bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        st.session_state.data[ticker] = fetch_intraday_data(ticker, interval)
        bar.progress((i + 1) / len(tickers))
    st.success("✅ Intraday data downloaded!")

# -------------------- Chart Display --------------------
if "data" not in st.session_state or not st.session_state.data:
    st.info("📌 Click the button above to load intraday data.")
else:
    empty = True
    for i in range(0, len(tickers), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(tickers):
                break
            symbol = tickers[idx]
            df = st.session_state.data.get(symbol)
            if df is None or df.empty:
                cols[j].warning(f"No intraday data for {symbol}")
                continue
            empty = False
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1)
            ax.set_title(symbol, fontsize=11)
            ax.set_ylabel("Close", fontsize=9)
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 10)))  # ✅ 10-min tick spacing
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)
    if empty:
        st.warning("⚠️ No data returned for any ticker. Try after 9:15 AM IST.")
