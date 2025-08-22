# whale_monitor.py
# TC Futures Dashboard (Coinglass API)

import streamlit as st
import requests

API_KEY = "a103f20a763d4ad0a39f15aa7bb8d6ec"
HEADERS = {"coinglassSecret": API_KEY}

# ===== Hàm lấy dữ liệu an toàn =====
def fetch_data(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.warning(f"Lỗi API {url}: {resp.status_code}")
            return None
    except Exception as e:
        st.error(f"Lỗi khi gọi API {url}: {e}")
        return None

# ===== Layout Streamlit =====
st.set_page_config(page_title="TC Futures Dashboard", layout="wide")
st.title("📊 TC Futures Dashboard (Coinglass API)")

# --- Spot Price ---
spot_data = fetch_data("https://open-api-v4.coinglass.com/api/coin/spot_chart?symbol=BTC")
if spot_data and "data" in spot_data and spot_data["data"]:
    spot_price = spot_data["data"][-1]["c"]  # lấy close price cuối cùng
    st.metric("Spot Price (USD)", f"{float(spot_price):,.2f}")
else:
    st.metric("Spot Price (USD)", "—")

# --- Open Interest ---
oi_data = fetch_data("https://open-api-v4.coinglass.com/api/futures/open_interest_chart?symbol=BTC")
if oi_data and "data" in oi_data and oi_data["data"]:
    oi_value = oi_data["data"][-1]["sumOpenInterest"]
    st.metric("Futures OI (USD)", f"{float(oi_value):,.2f}")
else:
    st.metric("Futures OI (USD)", "—")

# --- Funding Rate ---
fund_data = fetch_data("https://open-api-v4.coinglass.com/api/futures/funding_rates?symbol=BTC")
if fund_data and "data" in fund_data and "binance" in fund_data["data"]:
    funding_rate = fund_data["data"]["binance"][-1]["rate"]
    st.metric("Funding Rate (Binance)", f"{funding_rate:.4%}")
else:
    st.metric("Funding Rate (Binance)", "—")

# --- Liquidation Heatmap ---
st.subheader("📉 Liquidation Heatmap (BTC)")
liq_data = fetch_data("https://open-api-v4.coinglass.com/api/futures/liquidation_heatmap?symbol=BTC")
if liq_data and "data" in liq_data:
    st.json(liq_data["data"])
else:
    st.write("Không lấy được dữ liệu")
