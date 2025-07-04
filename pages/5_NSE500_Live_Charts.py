# --- Trigger data download only once ---
if "intraday_data" not in st.session_state:
    st.session_state.intraday_data = {}
    st.info("📥 Downloading intraday data...")
    bar = st.progress(0)
    valid_count = 0

    for i, ticker in enumerate(tickers):
        df = fetch_intraday(ticker)
        if not df.empty and "Close" in df.columns and not df["Close"].dropna().empty:
            st.session_state.intraday_data[ticker] = df
            valid_count += 1
        bar.progress((i + 1) / len(tickers))

    bar.empty()
    if valid_count == 0:
        st.error("❌ No valid intraday data was returned. Market might be closed or data not yet available.")
    else:
        st.success(f"✅ Download complete. Valid tickers: {valid_count}")
