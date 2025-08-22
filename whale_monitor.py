import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="BTC Dashboard", layout="wide")
st.title("📊 BTC Dashboard — Giá, OI, Funding, Heatmap")

# ----------- Lấy dữ liệu từ Binance -----------
def get_binance_data():
    try:
        # Giá BTC (Binance Futures)
        r_price = requests.get("https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT")
        price = float(r_price.json()["price"])

        # Funding Rate
        r_funding = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT")
        data_funding = r_funding.json()
        funding_rate = float(data_funding["lastFundingRate"])
        next_funding_time = int(data_funding["nextFundingTime"])

        # Open Interest (approx: not directly from Binance, cần Coinglass để chuẩn)
        r_oi = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT")
        oi = float(r_oi.json()["openInterest"])

        return price, funding_rate, next_funding_time, oi, None
    except Exception as e:
        return None, None, None, None, str(e)

price, funding_rate, next_funding_time, oi, err = get_binance_data()

if err:
    st.error(f"Lỗi khi lấy dữ liệu: {err}")
    st.stop()

# ----------- Hiển thị Metrics -----------
col1, col2, col3 = st.columns(3)
col1.metric("Giá BTC/USDT", f"{price:,.2f} $")
col2.metric("Open Interest (BTC)", f"{oi:,.2f}")
col3.metric("Funding Rate", f"{funding_rate*100:.4f} %")

# ----------- Hiển thị Heatmap (Coinglass iframe) -----------
st.header("📉 Liquidation Heatmap")
st.markdown(
    """
    <iframe src="https://www.coinglass.com/LiquidationMap?symbol=BTC"
    width="100%" height="600" frameborder="0"></iframe>
    """,
    unsafe_allow_html=True
)

st.caption("Nguồn dữ liệu: Binance Futures + Coinglass")
