import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from streamlit.components.v1 import html
import requests
import os
import glob
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Auto‐reload every 30 seconds
# ─────────────────────────────────────────────────────────────────────────────
html(
    """
    <script>
      setTimeout(() => { window.location.reload(); }, 30000);
    </script>
    """,
    height=0,
)

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Live Intraday Charts", layout="wide")
st.title("🔄 Live Intraday Charts (1-min) — Gainers & Losers from NSE")

DATA_DIR = "data/TOP-Gain-loosers"
os.makedirs(DATA_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# NSE Fetcher — Save to CSV
# ─────────────────────────────────────────────────────────────────────────────
def fetch_nse_data(index_type):
    url = f"https://www.nseindia.com/api/live-analysis-variations?index={index_type}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    response = session.get(url, headers=headers)
    response.raise_for_status()
    return pd.DataFrame(response.json()["data"])

if st.button("📥 Fetch Gainers & Losers from NSE"):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        gainers_df = fetch_nse_data("gainers")
        losers_df  = fetch_nse_data("losers")

        g_path = os.path.join(DATA_DIR, f"T20-GL-gainers-auto-{today}.csv")
        l_path = os.path.join(DATA_DIR, f"T20-GL-losers-auto-{today}.csv")

        gainers_df.to_csv(g_path, index=False)
        losers_df.to_csv(l_path, index=False)

        st.success(f"Gainers & Losers saved for {today}")
    except Exception as e:
        st.error(f"❌ Error fetching from NSE: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Load latest CSVs (by modification time)
# ─────────────────────────────────────────────────────────────────────────────
def newest(pattern):
    files = glob.glob(os.path.join(DATA_DIR, pattern))
    return max(files, key=os.path.getmtime) if files else None

g_file = newest("*gainers*.csv")
l_file = newest("*losers*.csv")

if not g_file or not l_file:
    st.error("❗ Make sure you have gainers & losers CSVs available.")
    st.stop()

st.markdown(
    f"**🟢 Gainers CSV:** `{os.path.basename(g_file)}`  &nbsp; "
    f"**🔴 Losers CSV:** `{os.path.basename(l_file)}`"
)

# ─────────────────────────────────────────────────────────────────────────────
# Load tickers from CSV
# ─────────────────────────────────────────────────────────────────────────────
def load_syms(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.upper()
    if "SYMBOL" not in df.columns:
        st.error(f"`{os.path.basename(path)}` must have a SYMBOL column.")
        st.stop()
    syms = df["SYMBOL"].dropna().astype(str).str.upper()
    return [s if s.endswith(".NS") else f"{s}.NS" for s in syms]

gainers = load_syms(g_file)
losers  = load_syms(l_file)
st.success(f"✅ Loaded {len(gainers)} gainers and {len(losers)} losers.")

# ─────────────────────────────────────────────────────────────────────────────
# Fetch intraday data (1min) and cache for 30 seconds
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_intraday(sym):
    return yf.download(sym, period="1d", interval="1m", prepost=True,
                       progress=False, auto_adjust=True)

# ─────────────────────────────────────────────────────────────────────────────
# Download + Plot
# ─────────────────────────────────────────────────────────────────────────────
all_syms = gainers + losers
prog = st.progress(0)
intraday = {}
for i, s in enumerate(all_syms):
    intraday[s] = fetch_intraday(s)
    prog.progress((i + 1) / len(all_syms))
st.success("📊 All intraday data loaded!")

def plot_group(title, syms):
    st.header(title)
    for i in range(0, len(syms), 2):
        cols = st.columns(2)
        for j in (0, 1):
            idx = i + j
            if idx >= len(syms): break
            sym = syms[idx]
            df = intraday.get(sym, pd.DataFrame())
            if df.empty:
                cols[j].warning(f"No data for {sym}")
                continue

            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(df.index, df["Close"], lw=1)
            ax.set_title(sym)
            ax.xaxis.set_major_locator(MinuteLocator(5))
            ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
            ax.tick_params(labelbottom=False)
            plt.tight_layout()
            cols[j].pyplot(fig)
            plt.close(fig)

plot_group("🔼 Top Gainers", gainers)
plot_group("🔽 Top Losers",  losers)
