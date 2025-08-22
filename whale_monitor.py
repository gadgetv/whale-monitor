import streamlit as st
import requests

st.title("📊 TC Futures Dashboard (Coinglass API)")

# Binance Spot price (ổn định, không cần key)
spot_url = "https://api.binance.com/api/v3/ticker/price"
params = {"symbol": "BTCUSDT"}

try:
    spot_data = requests.get(spot_url, params=params, timeout=5).json()
    if "price" in spot_data:
        spot_price = float(spot_data["price"])
        st.metric("BTC Spot Price", f"{spot_price:,.2f} USDT")
    else:
        st.error(f"Lỗi: JSON không có 'price'. Raw JSON: {spot_data}")
except Exception as e:
    st.error(f"Lỗi khi lấy giá BTC Spot: {e}")
