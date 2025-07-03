import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta, timezone
import matplotlib.dates as mdates
import os

# -------------------- IST Time Handling --------------------
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Returns current time in IST, independent of server time zone."""
    return datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(IST)

def get_cache_date() -> str:
    now = get_ist_now()
    return now.date().isoformat()

CACHE_DATE = get_cache_date()

# -------------------- Page Setup --------------------
st.set_page_config(page_title="Today's Intraday Charts", layout="wide")
st.title("📊 Intraday Charts — From 9:15 AM (Nifty 500)")

# -------------------- Sidebar Filters --------------------
st.sidebar.header("🔍 Filter Stocks")

interval = st.sidebar.selectbox("Select Time Interval", options=["1m", "2m", "5m", "10m", "15m"], index=2)
apply_filters = st.sidebar.checkbox("✅ Apply Filters", value=True)

def load_tickers() -> list[str]:
    file_path = "data/Charts-data/tickers_Nitfy500.txt"
    if not os.path.exists(file_path):
        st.error(f"Ticker file not found: {file_path}")
        return []
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

tickers = load_tickers()

alphabet_options = sorted(set([symbol[0].upper() for symbol in tickers if symbol]))
selected_letter = st.sidebar.selectbox("Start with Letter", options=["All"] + list(alphabet_options), index=0)

price_min, price_max = 0, 10000
selected_range = st.sidebar.slider("Latest Price Range (Today)", min_value=price_min, max_value=price_max, value=(price_min, price_max), step=10)

# -------------------- Data Fetching --------------------
@st.cache_data(ttl=900)
def download_data(ticker: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period="1d", interval=interval, progress=False, auto_adjust=True)
    if df.empty:
        return df
    df.index = df.index.tz_localize(None)
    ist_today = get_ist_now().date()
    market_start = datetime.combine(ist_today, datetime.strptime("09:15", "%H:%M").time())
    df = df[df.index >= market_start]
    return df

@st.cache_data(ttl=86400)
def get_company_name(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker

# -------------------- Display Info --------------------
st.markdown(f"**🧾 Total Tickers:** {len(tickers)}")
st.markdown(f"**📅 Showing {interval} Data Since 9:15 AM IST — {CACHE_DATE}**")

# Warn if before 9:15 IST
if get_ist_now().time() < datetime.strptime("09:15", "%H:%M").time():
    st.warning("⚠️ Market opens at 9:15 AM IST. Please try again after that for today's data.")

# -------------------- Download Button --------------------
download_label = f"📥 Download Today’s {interval} Intraday Data for All Tickers"
if st.button(download_label):
    st.session_state.data = {}
    progress = st.progress(0)
    for i, symbol in enumerate(tickers):
        df = download_data(symbol, interval)
        st.session_state.data[symbol] = df
        progress.progress((i + 1) / len(tickers))

    non_empty = {k: v for k, v in st.session_state.data.items() if v is not None and not v.empty}
    st.session_state.data = non_empty

    if not non_empty:
        st.error("⚠️ No data downloaded. Market may be closed or Yahoo Finance has delayed today's data.")
    else:
        st.success(f"✅ Intraday ({interval}) data downloaded for {len(non_empty)} tickers.")

if "data" not in st.session_state or not st.session_state.data:
    st.info("📌 Please download intraday data first.")
    st.stop()

st.markdown(f"**📦 Tickers with Data:** {len(st.session_state.data)}")

# -------------------- Filtering Logic --------------------
filtered_tickers = []

for symbol, df in st.session_state.data.items():
    if df is None or df.empty:
        continue

    if apply_filters:
        if selected_letter != "All" and not symbol.upper().startswith(selected_letter):
            continue
        try:
            latest_price = float(df["Close"].dropna().iloc[-1])
        except:
            continue
        if not (selected_range[0] <= latest_price <= selected_range[1]):
            continue

    filtered_tickers.append(symbol)

# -------------------- Chart Display --------------------
if not filtered_tickers:
    st.warning("⚠️ No stocks found for the selected filters.")
else:
    for idx in range(0, len(filtered_tickers), 2):
        cols = st.columns(2)
        for col_i in range(2):
            if idx + col_i >= len(filtered_tickers):
                break
            symbol = filtered_tickers[idx + col_i]
            df = st.session_state.data.get(symbol)
            if df is None or df.empty:
                cols[col_i].warning(f"No intraday data for {symbol}.")
                continue

            name = get_company_name(symbol)
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], linewidth=1)
            ax.set_title(f"{symbol} — {name}", fontsize=11)
            ax.set_ylabel("Price", fontsize=9)
            ax.set_xlabel("Time", fontsize=8)

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            interval_minutes = int(interval.replace("m", ""))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=interval_minutes))
            ax.tick_params(axis="x", labelrotation=45, labelsize=7)
            ax.grid(True, linestyle="--", alpha=0.5)

            plt.tight_layout()
            cols[col_i].pyplot(fig)
            plt.close(fig)
