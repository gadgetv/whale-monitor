# -*- coding: utf-8 -*-
import streamlit as st
import requests

# ⚙️ Config API
API_KEY = "YOUR_COINGLASS_KEY"  # <-- thay bằng key của bạn
HEADERS = {"coinglassSecret": API_KEY}

st.set_page_config(page_title="TC Futures Dashboard", layout="wide")
st.title("📊 TC Futures Dashboard (Coinglass API)")

# 🟢 Hàm lấy dữ liệu từ Coinglass
def get_data(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu từ {url}: {e}")
        return {}

# 🔹 Spot Price
spot = get_data("https://open-api.coinglass.com/api/index/spot_price", {"symbol": "BTC"})
spot_price = spot.get("data", {}).get("price", 0)

# 🔹 Open Interest
oi = get_data("https://open-api.coinglass.com/api/futures/open_interest", {"symbol": "BTC"})
oi_value = oi.get("data", [{}])[0].get("openInterest", 0) if oi.get("data") else 0

# 🔹 Funding Rate
funding = get_data("https://open-api.coinglass.com/api/futures/funding_rates", {"symbol": "BTC"})
fund_rate = funding.get("data", [{}])[0].get("fundingRate", 0) if funding.get("data") else 0

# 🔹 Layout hiển thị
col1, col2, col3 = st.columns(3)
col1.metric("BTC Spot Price", f"{spot_price:,.2f} USDT")
col2.metric("Open Interest", f"{oi_value:,.2f}")
col3.metric("Funding Rate", f"{fund_rate*100:.4f} %")

# 🔹 Liquidation Heatmap
st.subheader("📉 Liquidation Heatmap (BTC)")
heatmap = get_data("https://open-api.coinglass.com/api/futures/liquidation_heatmap", {"symbol": "BTC"})
st.json(heatmap)  # hiển thị raw JSON trước
