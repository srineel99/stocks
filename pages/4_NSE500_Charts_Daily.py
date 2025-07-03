import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta, timezone
import matplotlib.dates as mdates

# -------------------- Timezone Setup --------------------
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(IST)

def get_cache_date() -> str:
    now = get_ist_now()
    return now.date().isoformat()

CACHE_DATE = get_cache_date()

# -------------------- Page Setup --------------------
st.set_page_config(page_title="Today's Intraday Charts", layout="wide")
st.title("📊 Intraday Charts — From 9:15 AM IST (Sample NSE Stocks)")

# -------------------- Sidebar Options --------------------
st.sidebar.header("🔍 Options")

interval = st.sidebar.selectbox("Select Interval", ["1m", "2m", "5m", "10m", "15m"], index=2)
show_all = st.sidebar.checkbox("Show All Charts", value=True)

# 🔧 Use only a few tickers to avoid Yahoo throttling
tickers = ["TATAMOTORS.NS", "RELIANCE.NS"]

st.markdown(f"**🧾 Total Tickers:** {len(tickers)}")
st.markdown(f"**📅 Showing {interval} Data Since 9:15 AM IST — {CACHE_DATE}**")

# -------------------- Data Fetching --------------------
@st.cache_data(ttl=900)
def download_data(ticker: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(
            tickers=ticker,
            period="1d",
            interval=interval,
            progress=False,
            auto_adjust=True,
            prepost=False,
            threads=False,
        )
        if df.empty:
            return pd.DataFrame()
        df.index = df.index.tz_localize(None)
        ist_today = get_ist_now().date()
        market_start = datetime.combine(ist_today, datetime.strptime("09:15", "%H:%M").time())
        return df[df.index >= market_start]
    except Exception as e:
        st.warning(f"⚠️ Error fetching {ticker}: {e}")
        return pd.DataFrame()

# -------------------- Button to Load Data --------------------
if st.button(f"📥 Load {interval} Intraday Data"):
    st.session_state.data = {}
    for symbol in tickers:
        df = download_data(symbol, interval)
        st.session_state.data[symbol] = df

    non_empty = {k: v for k, v in st.session_state.data.items() if not v.empty}
    st.session_state.data = non_empty

    if not non_empty:
        st.error("❌ No data returned for any ticker. Please try after 9:15 AM IST.")
    else:
        st.success(f"✅ Loaded data for {len(non_empty)} tickers.")

if "data" not in st.session_state or not st.session_state.data:
    st.info("📌 Click the button above to load intraday data.")
    st.stop()

# -------------------- Show Charts --------------------
for idx, symbol in enumerate(st.session_state.data):
    df = st.session_state.data[symbol]
    if df.empty:
        continue

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(df.index, df["Close"], linewidth=1.2)
    ax.set_title(f"{symbol}", fontsize=12)
    ax.set_ylabel("Price", fontsize=10)
    ax.set_xlabel("Time", fontsize=9)

    # Format x-axis as time
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    interval_minutes = int(interval.replace("m", ""))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=interval_minutes))
    ax.tick_params(axis="x", labelrotation=45, labelsize=8)
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    if not show_all:
        break
