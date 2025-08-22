import streamlit as st
import requests

BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
BINANCE_OI_URL = "https://fapi.binance.com/fapi/v1/openInterest"
SYMBOL = "BTCUSDT"

def fetch_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu từ {url}: {e}")
        return {}

# Kiểm tra Premium Index
st.subheader("Raw JSON — Premium Index (Funding/Mark Price)")
raw_premium = fetch_json(BINANCE_FUNDING_URL, {"symbol": SYMBOL})
st.json(raw_premium)

# Kiểm tra Open Interest
st.subheader("Raw JSON — Open Interest")
raw_oi = fetch_json(BINANCE_OI_URL, {"symbol": SYMBOL})
st.json(raw_oi)

# Sau khi xem raw JSON hiển thị, mới parse dữ liệu
if isinstance(raw_premium, list):
    raw_premium = raw_premium[0]

mark_price = float(raw_premium.get("markPrice", 0))
funding_rate = float(raw_premium.get("lastFundingRate", 0))
oi_base = float(raw_oi.get("openInterest", 0))

st.metric("Mark Price", f"{mark_price:,.2f} USDT")
st.metric("Funding Rate", f"{funding_rate*100:.4f} %")
st.metric("Open Interest", f"{oi_base:,.0f}")
