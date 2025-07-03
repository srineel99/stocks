import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, time, timedelta, timezone
import os

# -------------------- IST TIMEZONE SETUP --------------------
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_date_str = now_ist.date().isoformat()

# -------------------- CONFIGURATION --------------------
st.set_page_config(page_title="NSE500 Charts Daily", layout="wide")
st.title("📊 Intraday Charts — From 9:15 AM IST (Sample NSE Stocks)")
st.markdown(f"📅 **Showing 5m Data Since 9:15 AM IST — `{today_date_str}`**")

# -------------------- SAMPLE TICKERS (Replace with actual NSE500 list) --------------------
tickers = ["TATAMOTORS.NS", "RELIANCE.NS"]
st.markdown(f"🧾 **Total Tickers:** {len(tickers)}")

# -------------------- SIDEBAR OPTIONS --------------------
st.sidebar.header("🔍 Options")
interval = st.sidebar.selectbox("Select Interval", ["1m", "2m", "5m", "10m", "15m"], index=2)
show_all = st.sidebar.checkbox("✅ Show All Charts", value=True)

# -------------------- DOWNLOAD DATA --------------------
@st.cache_data(ttl=600)
def fetch_data(symbol: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(
            symbol, 
            period="1d", 
            interval=interval, 
            progress=False, 
            auto_adjust=True, 
            prepost=False
        )
        df = df[df.index >= datetime.combine(now_ist.date(), time(9, 15)).replace(tzinfo=IST)]
        return df
    except Exception:
        return pd.DataFrame()

if st.button(f"📥 Load {interval} Intraday Data"):
    st.session_state.data = {}
    bar = st.progress(0)
    for i, sym in enumerate(tickers):
        st.session_state.data[sym] = fetch_data(sym, interval)
        bar.progress((i + 1) / len(tickers))
    st.success(f"✅ {interval} intraday data downloaded successfully!")

# -------------------- DISPLAY CHARTS --------------------
if "data" not in st.session_state or not st.session_state.data:
    st.warning("📌 Click the button above to load intraday data.")
else:
    empty = True
    for i in range(0, len(tickers), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(tickers):
                break
            symbol = tickers[idx]
            df = st.session_state.data.get(symbol, pd.DataFrame())
            if df is None or df.empty:
                cols[j].error(f"No intraday data for {symbol}. Please try after 9:15 AM IST.")
                continue
            empty = False
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1)
            ax.set_title(f"{symbol}", fontsize=11)
            ax.set_ylabel("Close", fontsize=9)
            ax.xaxis.set_major_locator(MinuteLocator(interval=5))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)
    if empty:
        st.warning("⚠️ No data returned for any ticker. Please try after 9:15 AM IST.")

