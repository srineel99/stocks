import streamlit as st
import glob, os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from streamlit.components.v1 import html

# ─────────────────────────────────────────────────────────────────────────────
# Auto‐reload entire page every 30 seconds via browser
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
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Live Intraday Charts", layout="wide")
st.title("🔄 Live Intraday Charts (1-min) — Gainers & Losers from CSV")

# ─────────────────────────────────────────────────────────────────────────────
# Where your CSVs live
# ─────────────────────────────────────────────────────────────────────────────
GAIN_LOSS_DIR = r"C:\Streamlit\data\TOP-Gain-loosers"

# ─────────────────────────────────────────────────────────────────────────────
# Find the newest gainers / loosers CSV by modification time
# ─────────────────────────────────────────────────────────────────────────────
def newest(pattern):
    files = glob.glob(os.path.join(GAIN_LOSS_DIR, pattern))
    return max(files, key=os.path.getmtime) if files else None

g_file = newest("*gainers*.csv")
l_file = newest("*loosers*.csv")

if not g_file or not l_file:
    st.error("Make sure you have at least one `*gainers*.csv` and one `*loosers*.csv` in your folder.")
    st.stop()

st.markdown(
    f"**Gainers CSV:** `{os.path.basename(g_file)}`  &nbsp; "
    f"**Losers CSV:** `{os.path.basename(l_file)}`"
)

# ─────────────────────────────────────────────────────────────────────────────
# Load SYMBOL column and normalize to .NS
# ─────────────────────────────────────────────────────────────────────────────
def load_syms(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.upper()
    if "SYMBOL" not in df.columns:
        st.error(f"`{os.path.basename(path)}` needs a SYMBOL column.")
        st.stop()
    syms = df["SYMBOL"].dropna().astype(str).str.upper()
    return [s if s.endswith(".NS") else f"{s}.NS" for s in syms]

gainers = load_syms(g_file)
losers  = load_syms(l_file)
st.success(f"Loaded {len(gainers)} gainers and {len(losers)} losers.")

# ─────────────────────────────────────────────────────────────────────────────
# Fetch intraday (1d/1m) & cache for 30 s so back-to-back requests aren’t duplicated
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_intraday(sym):
    return yf.download(sym, period="1d", interval="1m", prepost=True,
                       progress=False, auto_adjust=True)

all_syms = gainers + losers
prog = st.progress(0)
intraday = {}
for i, s in enumerate(all_syms):
    intraday[s] = fetch_intraday(s)
    prog.progress((i+1)/len(all_syms))
st.success("✅ All intraday data loaded!")

# ─────────────────────────────────────────────────────────────────────────────
# Plot helper (two columns per row, hide labels but keep 5-min ticks)
# ─────────────────────────────────────────────────────────────────────────────
def plot_group(title, syms):
    st.header(title)
    for i in range(0, len(syms), 2):
        cols = st.columns(2)
        for j in (0,1):
            idx = i+j
            if idx >= len(syms): break
            sym = syms[idx]
            df  = intraday.get(sym, pd.DataFrame())
            if df.empty:
                cols[j].warning(f"No data for {sym}")
                continue

            fig, ax = plt.subplots(figsize=(6,3))
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
