import streamlit as st
import glob, os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from streamlit.components.v1 import html

html("""
    <script>
      setTimeout(() => { window.location.reload(); }, 30000);
    </script>
""", height=0)

st.set_page_config(page_title="Live Intraday Charts", layout="wide")
st.title("🔄 Live Intraday Charts (1-min) — Gainers & Losers from CSV")

base_dir = os.path.dirname(__file__)
GAIN_LOSS_DIR = os.path.abspath(os.path.join(base_dir, "..", "data", "TOP-Gain-loosers"))

def newest(pattern):
    files = glob.glob(os.path.join(GAIN_LOSS_DIR, pattern))
    return max(files, key=os.path.getmtime) if files else None

g_file = newest("*gainers*.csv")
l_file = newest("*loosers*.csv")

if not g_file or not l_file:
    st.error("❌ Missing required CSVs: Ensure at least one `*gainers*.csv` and `*loosers*.csv` are present.")
    st.stop()

st.markdown(
    f"📄 **Gainers CSV:** `{os.path.basename(g_file)}` &nbsp;&nbsp;&nbsp;&nbsp; "
    f"📄 **Losers CSV:** `{os.path.basename(l_file)}`"
)

def load_syms(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.upper()
    if "SYMBOL" not in df.columns:
        st.error(f"❌ `{os.path.basename(path)}` must contain a `SYMBOL` column.")
        st.stop()
    syms = df["SYMBOL"].dropna().astype(str).str.strip().str.upper()
    return [s if s.endswith(".NS") else f"{s}.NS" for s in syms]

gainers = load_syms(g_file)
losers  = load_syms(l_file)
st.success(f"✅ Loaded {len(gainers)} gainers and {len(losers)} losers.")

@st.cache_data(ttl=30)
def fetch_intraday(sym):
    return yf.download(sym, period="1d", interval="1m", prepost=True,
                       progress=False, auto_adjust=True)

all_syms = gainers + losers
prog = st.progress(0)
intraday = {}
for i, sym in enumerate(all_syms):
    try:
        intraday[sym] = fetch_intraday(sym)
    except Exception:
        intraday[sym] = pd.DataFrame()
    prog.progress((i + 1) / len(all_syms))

st.success("📊 Intraday data loaded for all tickers.")

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
                cols[j].warning(f"No intraday data for {sym}")
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
