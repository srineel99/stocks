import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from datetime import datetime, time, timedelta, timezone
import os, time as systime

# -------------------- Timezone Setup (IST) --------------------
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# -------------------- Page Setup --------------------
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
        df.index = pd.to_datetime(df.index).tz_localize(None)
        start_time = datetime.combine(now_ist.date(), time(9, 15))
        return df[df.index >= start_time]
    except:
        return pd.DataFrame()

# -------------------- Trend Classification --------------------
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

# -------------------- Download Button --------------------
if "data" not in st.session_state or st.button("📥 Load Intraday Data"):
    st.session_state.data = {"ascending": [], "descending": [], "flat": []}
    bar = st.progress(0, text="⏳ Fetching fresh 5m data...")

    for i, ticker in enumerate(tickers):
        df = fetch_intraday_data(ticker)
        trend, slope = classify_trend(df)
        if not df.empty:
            st.session_state.data[trend].append((ticker, df, slope))
        systime.sleep(0.4)  # reduce delay slightly for performance
        bar.progress((i + 1) / len(tickers))
    bar.empty()
    st.success("✅ Intraday data downloaded and grouped!")

# -------------------- Fixed IST Time Ticks --------------------
def get_ist_ticks():
    return pd.date_range(
        start=datetime.combine(now_ist.date(), time(9, 15)),
        end=datetime.combine(now_ist.date(), time(15, 30)),
        freq="15min"
    )

# -------------------- Chart Plotting --------------------
def plot_chart(symbol, df, slope):
    try:
        slope_val = float(slope)
    except:
        slope_val = 0.0
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df.index, df["Close"], lw=1.2)
    ax.set_title(f"{symbol} (slope={slope_val:.2f})", fontsize=10)
    ax.set_ylabel("Close", fontsize=8)
    ax.set_xticks(get_ist_ticks())
    ax.set_xticklabels([t.strftime("%H:%M") for t in get_ist_ticks()], rotation=45, ha="right", fontsize=7)
    ax.set_xlim(get_ist_ticks()[0], get_ist_ticks()[-1])
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

# -------------------- Display All Trend Groups --------------------
if "data" not in st.session_state or not any(st.session_state.data.values()):
    st.warning("⚠️ No data to display. Click '📥 Load Intraday Data' to start.")
else:
    display_group("📈 Ascending (≈ +45°) Charts", st.session_state.data["ascending"])
    display_group("📉 Descending (≈ -45°) Charts", st.session_state.data["descending"])
    display_group("➡️ Flat/Other Charts", st.session_state.data["flat"])
