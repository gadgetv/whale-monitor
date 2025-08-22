import streamlit as st
import requests

API_KEY = "YOUR_COINGLASS_KEY"  # 🔑 thay bằng key của bạn
headers = {"coinglassSecret": a103f20a763d4ad0a39f15aa7bb8d6ec}

st.title("📊 BTC Futures Dashboard (Coinglass API)")

# ✅ Spot Price từ Binance
spot_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
spot_price = requests.get(spot_url).json()
st.metric("BTC Spot Price", f"{float(spot_price['price']):,.2f} USDT")

# ✅ Funding Rate từ Coinglass
funding_url = "https://open-api.coinglass.com/api/futures/funding_rates?symbol=BTC"
funding_data = requests.get(funding_url, headers=headers).json()
if funding_data.get("data"):
    binance_funding = [f for f in funding_data["data"] if f["exchangeName"] == "Binance"]
    if binance_funding:
        rate = float(binance_funding[0]["rate"]) * 100
        st.metric("Funding Rate (Binance)", f"{rate:.4f} %")
    else:
        st.warning("Không có dữ liệu Funding Binance")

# ✅ Open Interest từ Coinglass
oi_url = "https://open-api.coinglass.com/api/futures/openInterest?symbol=BTC"
oi_data = requests.get(oi_url, headers=headers).json()
if oi_data.get("data"):
    binance_oi = [f for f in oi_data["data"] if f["exchangeName"] == "Binance"]
    if binance_oi:
        st.metric("Open Interest (Binance)", f"{binance_oi[0]['openInterest']} USDT")
