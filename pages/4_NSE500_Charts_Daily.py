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
st.set_page_config(page_title="NSE500 Intraday Charts", layout="wide")
st.title("📊 Intraday Charts — From 9:15 AM IST (Nifty 500)")
st.markdown(f"📅 **Showing {today_str} Intraday Charts From 9:15 AM IST**")

# -------------------- Load Tickers --------------------
@st.cache_data
def load_tickers():
    path = "data/Charts-data/tickers_Nitfy500.txt"
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

# -------------------- Fetch Function --------------------
def fetch_intraday_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="1d",
            interval="5m",
            progress=False,
            auto_adjust=True
        )
        if df.empty:
            return df
        df.index = df.index.tz_localize('UTC').tz_convert(IST)  # ✅ Convert to IST
        df = df[df.index >= datetime.combine(now_ist.date(), time(9, 15)).replace(tzinfo=IST)]
        return df
    except:
        return pd.DataFrame()

# -------------------- Fetch & Plot --------------------
st.info("🔄 Fetching fresh intraday data (5m interval)...")
data_dict = {}
bar = st.progress(0)
for i, ticker in enumerate(tickers):
    df = fetch_intraday_data(ticker)
    data_dict[ticker] = df
    bar.progress((i + 1) / len(tickers))
st.success("✅ Live intraday data loaded!")

# -------------------- Display Charts --------------------
empty = True
for i in range(0, len(tickers), 2):
    cols = st.columns(2)
    for j in range(2):
        idx = i + j
        if idx >= len(tickers):
            break
        symbol = tickers[idx]
        df = data_dict.get(symbol)
        if df is None or df.empty:
            cols[j].warning(f"No intraday data for {symbol}")
            continue
        empty = False
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(df.index, df["Close"], lw=1)
        ax.set_title(symbol, fontsize=11)
        ax.set_ylabel("Close", fontsize=9)
        ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))  # ✅ X-axis every 15 min
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
        plt.tight_layout()
        cols[j].pyplot(fig)
        plt.close(fig)
if empty:
    st.warning("⚠️ No data returned for any ticker. Try after 9:15 AM IST.")
