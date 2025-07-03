import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
import os
import random
import numpy as np
from scipy.stats import linregress

# --- IST Timezone setup ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Page config ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing **{today_str}** data — Starting from first available tick after 9:00 AM IST")

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
st.markdown(f"📈 **Total Tickers:** {len(tickers)}")

# --- Download intraday data (cached) ---
@st.cache_data(ttl=600)
def fetch_intraday(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        df = df.tz_convert(IST).tz_localize(None)  # Convert to IST and make naive
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return pd.DataFrame()

# --- Angle Calculation Function ---
def calculate_angle(df):
    if len(df) < 2:
        return 0
    
    x = np.arange(len(df))
    y = df['Close'].values
    
    slope, _, _, _, _ = linregress(x, y)
    angle = np.degrees(np.arctan(slope))
    
    return angle

# --- Main App Logic ---
if 'intraday_data' not in st.session_state or 'angles' not in st.session_state:
    st.session_state.intraday_data = {}
    st.session_state.angles = {}

if not st.session_state.intraday_data:
    st.info("📥 Fetching live intraday data (1m interval)...")
    bar = st.progress(0)
    random.shuffle(tickers)
    
    successful_loads = 0
    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty:
            st.session_state.intraday_data[ticker] = df
            angle = calculate_angle(df)
            st.session_state.angles[ticker] = angle
            successful_loads += 1
        bar.progress((i + 1) / len(tickers))
    
    if successful_loads > 0:
        st.success(f"✅ Successfully loaded data for {successful_loads}/{len(tickers)} tickers")
    else:
        st.error("❌ Failed to load data for any tickers. Please check your internet connection and try again.")
        st.stop()

# --- Filter Options ---
st.sidebar.header("Chart Filters")
angle_filter = st.sidebar.selectbox(
    "Sort by angle:",
    ["All", "Ascending (~45°)", "Descending (~-45°)", "Steep Ascending (>60°)", "Steep Descending (<-60°)"]
)

# --- Sort tickers based on angle ---
def sort_tickers_by_angle(tickers, angles, filter_option):
    if filter_option == "All":
        return [t for t in tickers if t in st.session_state.intraday_data]
    
    filtered = []
    for ticker in tickers:
        if ticker not in st.session_state.intraday_data:
            continue
        angle = angles.get(ticker, 0)
        if filter_option == "Ascending (~45°)" and 30 <= angle <= 60:
            filtered.append(ticker)
        elif filter_option == "Descending (~-45°)" and -60 <= angle <= -30:
            filtered.append(ticker)
        elif filter_option == "Steep Ascending (>60°)" and angle > 60:
            filtered.append(ticker)
        elif filter_option == "Steep Descending (<-60°)" and angle < -60:
            filtered.append(ticker)
    
    filtered.sort(key=lambda x: abs(angles.get(x, 0)), reverse=True)
    return filtered

# --- Plot Charts ---
data = st.session_state.intraday_data
angles = st.session_state.angles

if data:
    sorted_tickers = sort_tickers_by_angle(list(data.keys()), angles, angle_filter)
    
    if not sorted_tickers and angle_filter != "All":
        st.warning(f"No charts match the {angle_filter} filter")
    else:
        count = 0
        for i in range(0, len(sorted_tickers), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j >= len(sorted_tickers):
                    break
                symbol = sorted_tickers[i + j]
                df = data[symbol]
                angle = angles.get(symbol, 0)

                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(df.index, df["Close"], lw=1.2)
                
                title = f"{symbol} (Angle: {angle:.1f}°)"
                if angle > 45:
                    title += " ↗↗"
                elif angle > 15:
                    title += " ↗"
                elif angle < -45:
                    title += " ↘↘"
                elif angle < -15:
                    title += " ↘"
                
                ax.set_title(title, fontsize=10)
                ax.set_ylabel("Price", fontsize=9)
                ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 15)))
                ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
                plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
                plt.tight_layout()
                cols[j].pyplot(fig)
                plt.close(fig)
                count += 1

        st.markdown(f"**Displaying {count} charts**")
else:
    st.error("No data available. Please refresh the page.")
