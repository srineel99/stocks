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
if not tickers:
    st.error("No tickers loaded. Check your ticker file.")
    st.stop()

st.markdown(f"📈 **Total Tickers:** {len(tickers)}")

# --- Download intraday data ---
def fetch_intraday_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        if df.empty:
            return None
        df = df.tz_convert(IST).tz_localize(None)
        df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
        return df
    except Exception as e:
        st.warning(f"Failed to fetch {ticker}: {str(e)}")
        return None

# --- Angle Calculation ---
def calculate_angle(df):
    if len(df) < 2:
        return 0
    x = np.arange(len(df))
    y = df['Close'].values
    slope, _, _, _, _ = linregress(x, y)
    return np.degrees(np.arctan(slope))

# --- Main App ---
if 'data_loaded' not in st.session_state:
    # Initial load
    st.session_state.intraday_data = {}
    st.session_state.angles = {}
    st.session_state.data_loaded = False

if not st.session_state.data_loaded:
    with st.status("📥 Downloading live data...", expanded=True) as status:
        progress_bar = st.progress(0)
        success_count = 0
        
        for i, ticker in enumerate(tickers):
            df = fetch_intraday_data(ticker)
            if df is not None:
                st.session_state.intraday_data[ticker] = df
                st.session_state.angles[ticker] = calculate_angle(df)
                success_count += 1
            progress_bar.progress((i + 1) / len(tickers))
        
        if success_count > 0:
            st.session_state.data_loaded = True
            status.update(label=f"✅ Downloaded {success_count}/{len(tickers)} tickers", state="complete")
        else:
            status.update(label="❌ Failed to download any data", state="error")
            st.error("No data could be loaded. Please check your internet connection and try again.")
            st.stop()

# --- Filter UI ---
st.sidebar.header("Chart Filters")
filter_option = st.sidebar.selectbox(
    "Trend Angle:",
    ["All", "Strong Up (45°+)", "Moderate Up (15-45°)", 
     "Moderate Down (-15-45°)", "Strong Down (-45°-)", 
     "Flat (-15° to 15°)"]
)

# --- Filter Logic ---
def filter_charts():
    filtered = []
    for ticker, df in st.session_state.intraday_data.items():
        angle = st.session_state.angles.get(ticker, 0)
        
        if filter_option == "All":
            filtered.append((ticker, angle))
        elif filter_option == "Strong Up (45°+)" and angle >= 45:
            filtered.append((ticker, angle))
        elif filter_option == "Moderate Up (15-45°)" and 15 <= angle < 45:
            filtered.append((ticker, angle))
        elif filter_option == "Moderate Down (-15-45°)" and -45 < angle <= -15:
            filtered.append((ticker, angle))
        elif filter_option == "Strong Down (-45°-)" and angle <= -45:
            filtered.append((ticker, angle))
        elif filter_option == "Flat (-15° to 15°)" and -15 < angle < 15:
            filtered.append((ticker, angle))
    
    # Sort by absolute angle (strongest trends first)
    filtered.sort(key=lambda x: abs(x[1]), reverse=True)
    return filtered

# --- Display Charts ---
filtered_tickers = filter_charts()

if not filtered_tickers:
    st.warning("No charts match the current filter")
else:
    st.success(f"Showing {len(filtered_tickers)} charts")
    
    cols = st.columns(2)
    for i, (ticker, angle) in enumerate(filtered_tickers):
        df = st.session_state.intraday_data[ticker]
        
        with cols[i % 2]:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], color='steelblue', linewidth=1.5)
            
            # Enhanced title with angle indicator
            angle_icon = ""
            if angle >= 45: angle_icon = "↗↗"
            elif angle >= 15: angle_icon = "↗"
            elif angle <= -45: angle_icon = "↘↘"
            elif angle <= -15: angle_icon = "↘"
            
            ax.set_title(f"{ticker} {angle_icon} ({angle:.1f}°)", 
                        fontsize=10, pad=10, color='navy')
            ax.set_ylabel("Price", fontsize=8)
            
            # Format x-axis
            ax.xaxis.set_major_locator(MinuteLocator(byminute=range(0, 60, 30)))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            plt.xticks(rotation=45, ha='right', fontsize=7)
            
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

# Refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.session_state.clear()
    st.rerun()
