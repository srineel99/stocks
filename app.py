import streamlit as st

st.set_page_config(
    page_title="Stock Dashboard",
    layout="wide",
)

st.title("📊 Stock Dashboard")

st.markdown(
    """
    Welcome!  

    Use the page selector in the sidebar (upper-left) to choose:

    - **NSE500 Charts**  
    - **Top Gainers / Losers**  
    - **NSE500 Weekly-Charts**  
    """
)
