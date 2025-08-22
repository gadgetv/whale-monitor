import streamlit as st
import requests

# ==============================
# ⚙️ Cấu hình API
# ==============================
API_KEY = "a103f20a763d4ad0a39f15aa7bb8d6ec"
BASE = "https://open-api-v4.coinglass.com"
HEADERS = {"coinglassSecret": API_KEY}


def fetch_json(path, params=None):
    """Hàm lấy dữ liệu JSON từ Coinglass API"""
    try:
        r = requests.get(BASE + path, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ==============================
# 📊 Streamlit App
# ==============================
st.set_page_config(page_title="TC Futures Dashboard", layout="wide")
st.title("📊 TC Futures Dashboard (Coinglass API)")

# -------- Spot Price --------
spot = fetch_json("/api/spot/coins-markets")
btc_price = None
if "data" in spot:
    for c in spot["data"]:
        if c.get("symbol") == "BTC":
            btc_price = c.get("current_price")

# -------- Futures OI --------
fut = fetch_json("/api/futures/coins-markets")
oi_total = None
if "data" in fut:
    for c in fut["data"]:
        if c.get("symbol") == "BTC":
            oi_total = c.get("open_interest_usd")

# -------- Funding Rate (Binance) --------
fund = fetch_json("/api/futures/fundingRate/exchange-list", {"symbol": "BTC"})
fund_binance = None
if "data" in fund and fund["data"]:
    for ex in fund["data"][0].get("stablecoin_margin_list", []):
        if ex["exchange"] == "Binance":
            fund_binance = ex["funding_rate"]

# -------- Liquidation Heatmap --------
heatmap = fetch_json("/api/futures/liquidation/heatmap/model1", {"symbol": "BTC"})

# ==============================
# 📈 Hiển thị kết quả
# ==============================
col1, col2, col3 = st.columns(3)
col1.metric("BTC Spot Price", f"{btc_price:,.2f} USDT" if btc_price else "—")
col2.metric("Open Interest (USD)", f"{oi_total:,.0f}" if oi_total else "—")
col3.metric("Funding Rate (Binance)", f"{fund_binance*100:.4f}%" if fund_binance else "—")

st.subheader("📉 Liquidation Heatmap (BTC)")
if "data" in heatmap:
    st.json(heatmap["data"])
else:
    st.error(heatmap.get("error", "Không lấy được dữ liệu"))
