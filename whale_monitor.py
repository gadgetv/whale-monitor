import streamlit as st
import requests

st.title("📈 BTC Spot Price Dashboard")

url = "https://api.binance.com/api/v3/ticker/price"
params = {"symbol": "BTCUSDT"}

try:
    data = requests.get(url, params=params, timeout=5).json()
    price = float(data["price"])
    st.metric("BTC Spot Price", f"{price:,.2f} USDT")
except Exception as e:
    st.error(f"Lỗi lấy giá BTC: {e}")
