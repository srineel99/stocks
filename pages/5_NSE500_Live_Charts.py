import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from datetime import datetime, timedelta, timezone
import os
import numpy as np
from scipy.stats import linregress

# --- Configuration ---
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
today_str = now_ist.date().isoformat()

# --- Setup with Error Prevention ---
st.set_page_config(page_title="NSE500 Live Charts", layout="wide")
st.title("📡 NSE500 Live Charts (Intraday)")
st.markdown(f"📅 Showing **{today_str}** data — Starting from first available tick after 9:00 AM IST")

# --- Ticker Loading with Validation ---
@st.cache_data
def load_tickers():
    try:
        path = "data/Charts-data/tickers_Nifty500.txt"
        if not os.path.exists(path):
            st.error(f"Ticker file not found: {path}")
            return None
        
        with open(path) as f:
            tickers = [
                line.strip().upper() + ".NS" if not line.strip().upper().endswith(".NS")
                else line.strip().upper()
                for line in f if line.strip()
            ]
            return tickers if tickers else None
    except Exception as e:
        st.error(f"Error loading tickers: {str(e)}")
        return None

tickers = load_tickers()
if not tickers:
    st.error("No valid tickers loaded. Check your ticker file.")
    st.stop()

st.markdown(f"📈 **Total Tickers:** {len(tickers)}")

# --- Enhanced Angle Calculation ---
def calculate_angle(df):
    try:
        if len(df) < 10:  # Need enough data points
            return 0.0
            
        # Normalize prices to percentage changes from open
        open_price = df['Close'].iloc[0]
        if open_price == 0:
            return 0.0
        normalized_prices = (df['Close'] - open_price) / open_price * 100
        
        # Use time in hours for x-axis
        time_hours = (df.index - df.index[0]).total_seconds() / 3600
        if time_hours[-1] == 0:  # Prevent division by zero
            return 0.0
            
        # Calculate regression on normalized data
        slope, _, _, _, _ = linregress(time_hours, normalized_prices)
        angle = np.degrees(np.arctan(slope))
        
        # Adjust angle sensitivity
        if abs(angle) > 70:  # Very steep trends
            return angle * 0.7  # Scale down extreme angles
        return angle
        
    except Exception:
        return 0.0

# --- Ultra-Safe Data Download ---
def fetch_intraday_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
        
        # Validate DataFrame structure
        if not isinstance(df, pd.DataFrame) or df.empty:
            return None
        if 'Close' not in df.columns:
            return None
            
        # Timezone handling
        try:
            df = df.tz_convert(IST).tz_localize(None)
            df = df[df.index >= datetime.combine(now_ist.date(), datetime.strptime("09:00", "%H:%M").time())]
            return df if not df.empty else None
        except:
            return None
    except:
        return None

# --- Main Application Flow ---
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'data': {},
        'angles': {},
        'loaded': False,
        'failed_tickers': []
    }

if not st.session_state.app_state['loaded']:
    with st.status("🚀 Loading market data...", expanded=True) as status:
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        successful = 0
        for i, ticker in enumerate(tickers):
            progress_text.text(f"Processing {ticker} ({i+1}/{len(tickers)})")
            progress_bar.progress((i + 1) / len(tickers))
            
            df = fetch_intraday_data(ticker)
            if df is not None:
                angle = calculate_angle(df)
                st.session_state.app_state['data'][ticker] = df
                st.session_state.app_state['angles'][ticker] = angle
                successful += 1
            else:
                st.session_state.app_state['failed_tickers'].append(ticker)
        
        if successful > 0:
            st.session_state.app_state['loaded'] = True
            status.update(
                label=f"✅ Loaded {successful}/{len(tickers)} tickers | {len(st.session_state.app_state['failed_tickers'])} failed",
                state="complete"
            )
        else:
            status.update(label="❌ All tickers failed to load", state="error")
            st.error("Critical failure. Please check your internet connection and try again.")
            st.stop()

# --- Enhanced Filtering Interface ---
st.sidebar.header("Trend Filters")
filter_choice = st.sidebar.selectbox(
    "Select Trend Type:",
    options=[
        "All Charts",
        "Strong Uptrend (≈45°)", 
        "Moderate Uptrend (15-45°)",
        "Sideways (-15° to 15°)",
        "Moderate Downtrend (-15° to -45°)",
        "Strong Downtrend (≈-45°)",
        "Very Steep (>60°)",
        "Very Steep (<-60°)"
    ],
    index=0
)

# --- Enhanced Filter Implementation ---
def apply_filter():
    filtered = []
    angles = st.session_state.app_state['angles']
    
    for ticker, df in st.session_state.app_state['data'].items():
        angle = angles.get(ticker, 0.0)
        
        if filter_choice == "All Charts":
            filtered.append((ticker, angle))
        elif filter_choice == "Strong Uptrend (≈45°)" and 35 <= angle <= 55:
            filtered.append((ticker, angle))
        elif filter_choice == "Moderate Uptrend (15-45°)" and 15 <= angle < 35:
            filtered.append((ticker, angle))
        elif filter_choice == "Sideways (-15° to 15°)" and -15 < angle < 15:
            filtered.append((ticker, angle))
        elif filter_choice == "Moderate Downtrend (-15° to -45°)" and -35 < angle <= -15:
            filtered.append((ticker, angle))
        elif filter_choice == "Strong Downtrend (≈-45°)" and -55 <= angle <= -35:
            filtered.append((ticker, angle))
        elif filter_choice == "Very Steep (>60°)" and angle > 60:
            filtered.append((ticker, angle))
        elif filter_choice == "Very Steep (<-60°)" and angle < -60:
            filtered.append((ticker, angle))
    
    # Sort by absolute angle (strongest trends first)
    return sorted(filtered, key=lambda x: abs(x[1]), reverse=True)

filtered_tickers = apply_filter()

# --- Enhanced Visualization ---
def plot_chart(ticker, df, angle):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    
    # Plot trend line
    time_hours = (df.index - df.index[0]).total_seconds() / 3600
    try:
        slope, intercept, *_ = linregress(time_hours, df['Close'])
        trend_line = slope * time_hours + intercept
        ax.plot(df.index, trend_line, '--', color='orange', alpha=0.7, linewidth=2, label='Trend Line')
    except:
        pass
    
    # Plot price
    color = 'green' if angle > 5 else 'red' if angle < -5 else 'gray'
    ax.plot(df.index, df['Close'], color=color, linewidth=2.5, label='Price')
    
    # Annotate angle
    ax.annotate(f"Angle: {angle:.1f}°", 
               xy=(0.02, 0.95), xycoords='axes fraction',
               bbox=dict(boxstyle='round', alpha=0.2))
    
    # Dynamic title with emoji indicators
    if angle >= 55: emoji = "🚀"
    elif angle >= 35: emoji = "📈↑↑"
    elif angle >= 15: emoji = "📈↑"
    elif angle <= -55: emoji = "💥" 
    elif angle <= -35: emoji = "📉↓↓"
    elif angle <= -15: emoji = "📉↓"
    else: emoji = "➡️"
    
    ax.set_title(
        f"{emoji} {ticker} ({angle:.1f}°)",
        fontsize=12,
        pad=12,
        color=color
    )
    
    # Axis formatting
    ax.set_ylabel("Price", fontsize=10)
    ax.xaxis.set_major_locator(MinuteLocator(byminute=[0, 30]))
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.grid(alpha=0.2)
    plt.legend()
    plt.tight_layout()
    
    return fig

# --- Display Charts ---
if not filtered_tickers:
    st.warning("No charts match the selected filter")
else:
    st.success(f"Displaying {len(filtered_tickers)} charts")
    
    cols = st.columns(2)
    for idx, (ticker, angle) in enumerate(filtered_tickers):
        df = st.session_state.app_state['data'][ticker]
        
        with cols[idx % 2]:
            try:
                fig = plot_chart(ticker, df, angle)
                st.pyplot(fig)
                plt.close(fig)
            except:
                st.warning(f"Couldn't display chart for {ticker}")

# --- Debug Information ---
if st.sidebar.checkbox("Show angle distribution"):
    angles = list(st.session_state.app_state['angles'].values())
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(angles, bins=30, color='skyblue', edgecolor='black')
    ax.set_title("Angle Distribution Across All Tickers", pad=15)
    ax.set_xlabel("Angle (degrees)", labelpad=10)
    ax.set_ylabel("Count", labelpad=10)
    ax.axvline(x=45, color='red', linestyle='--', alpha=0.5, label='45°')
    ax.axvline(x=-45, color='red', linestyle='--', alpha=0.5)
    ax.grid(alpha=0.2)
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)

# --- Refresh Mechanism ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Full Reset", help="Clear all cached data and reload", type="primary"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

# --- Failure Reporting ---
if st.session_state.app_state['failed_tickers']:
    with st.sidebar.expander("⚠️ Failed Tickers"):
        st.write(f"{len(st.session_state.app_state['failed_tickers'])} tickers failed to load:")
        st.code("\n".join(st.session_state.app_state['failed_tickers']))
