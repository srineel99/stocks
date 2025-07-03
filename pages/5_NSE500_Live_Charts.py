import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MinuteLocator
from datetime import datetime, timedelta, timezone
import numpy as np
import os

# --- Timezone for IST ---
IST = timezone(timedelta(hours=5, minutes=30))

def get_today():
    return datetime.now(IST).date().isoformat()

TODAY = get_today()

st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📈 NSE500 Live Charts")
st.markdown(f"""
### 📅 Showing: `{TODAY}`

🔄 Refresh the page to load latest data.
""")

# --- Sidebar chart group filter ---
st.sidebar.markdown("### 📁 Show Chart Group")
selected_group = st.sidebar.radio("Filter charts by trend", ["All", "Ascending (≈ +45°)", "Descending (≈ -45°)", "Neutral"])

# --- Load tickers ---
ticker_file = "data/Charts-data/tickers_Nifty500.txt"
with open(ticker_file) as f:
    tickers = [line.strip() for line in f if line.strip()]

@st.cache_data(ttl=300, show_spinner=False)
def fetch_intraday_data(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        df = df.between_time("09:00", "15:30")
        df = df.reset_index()
        df = df.rename(columns={"Datetime": "Time", "Close": "Price"})
        df = df[["Time", "Price"]].dropna()
        return df
    except:
        return None

# --- Calculate slope ---
def calculate_slope(df):
    y = df["Price"].values
    x = np.arange(len(y))
    if len(x) < 5 or np.std(y) == 0:
        return None
    try:
        slope, _ = np.polyfit(x, y, 1)
        return slope
    except Exception:
        return None

# --- Plot chart ---
def plot_chart(symbol, df, slope):
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.plot(df["Time"], df["Price"], linewidth=1)
    ax.set_title(f"{symbol}" + (f" (slope={slope:.2f})" if slope is not None else ""), fontsize=9)
    ax.set_ylabel("Price")
    ax.xaxis.set_major_locator(MinuteLocator(byminute=range(15, 60, 15)))
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# --- Grouping logic ---
ascending, descending, neutral = [], [], []
all_loaded = []

for symbol in tickers:
    df = fetch_intraday_data(symbol)
    if df is not None and len(df) > 5:
        slope = calculate_slope(df)
        if slope is not None:
            all_loaded.append((symbol, df, slope))
            if 0.40 <= slope <= 0.60:
                ascending.append((symbol, df, slope))
            elif -0.60 <= slope <= -0.40:
                descending.append((symbol, df, slope))
            else:
                neutral.append((symbol, df, slope))

st.success(f"📌 Total Tickers Loaded: `{len(all_loaded)}`")

# --- Display Group ---
def display_group(title, data):
    if not data:
        st.warning(f"No data available for {title}")
        return
    st.subheader(title)
    cols = st.columns(2)
    for i, (symbol, df, slope) in enumerate(data):
        with cols[i % 2]:
            st.pyplot(plot_chart(symbol, df, slope))

# --- Display based on selection ---
if selected_group == "All":
    display_group("\U0001F4C8 Ascending (≈ +45°)", ascending)
    display_group("\U0001F4C9 Descending (≈ -45°)", descending)
    display_group("\U0001F4CA Neutral", neutral)
elif selected_group.startswith("Ascending"):
    display_group("\U0001F4C8 Ascending (≈ +45°)", ascending)
elif selected_group.startswith("Descending"):
    display_group("\U0001F4C9 Descending (≈ -45°)", descending)
else:
    display_group("\U0001F4CA Neutral", neutral)
