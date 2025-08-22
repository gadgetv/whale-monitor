import streamlit as st
import requests
from datetime import datetime
from dateutil import tz

API_KEY = "a103f20a763d4ad0a39f15aa7bb8d6ec"
BASE = "https://open-api-v4.coinglass.com"
HEADERS = {"coinglassSecret": API_KEY}

def fetch_json(path, params=None):
    try:
        r = requests.get(BASE + path, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Lỗi API {path}: {e}")
        return {}

st.set_page_config(page_title="TC Futures Dashboard", layout="wide")
st.title("📊 TC Futures Dashboard (Coinglass API)")

# Spot Price
spot = fetch_json("/api/spot/coins-markets")
btc_price = next((c["current_price"] for c in spot.get("data", []) if c.get("symbol") == "BTC"), None)

# Futures: OI, Price, Funding avg
fut = fetch_json("/api/futures/coins-markets")
oi_usd = price_fut = avg_fr = None
for c in fut.get("data", []):
    if c.get("symbol") == "BTC":
        oi_usd = c.get("open_interest_usd")
        price_fut = c.get("current_price")
        avg_fr = c.get("avg_funding_rate_by_oi")
        break

# Funding Rate (Binance)
fund = fetch_json("/api/futures/fundingRate/exchange-list", {"symbol":"BTC"})
fr_binance = None
fr_next = None
if fund.get("data"):
    for ex in fund["data"][0].get("stablecoin_margin_list", []):
        if ex.get("exchange") == "Binance":
            fr_binance = ex.get("funding_rate")
            fr_next = ex.get("next_funding_time")
            break

# Display
col1, col2, col3 = st.columns(3)
col1.metric("Spot Price (USD)", f"{btc_price:,.2f}" if btc_price else "—")
col2.metric("Futures OI (USD)", f"{oi_usd:,.0f}" if oi_usd else "—")
if fr_binance is not None:
    dt = datetime.fromtimestamp(fr_next/1000, tz=tz.tzlocal()) if fr_next else ""
    col3.metric("Funding Rate (Binance)", f"{fr_binance*100:.4f} %", help=f"Next funding: {dt}")
else:
    col3.metric("Funding Rate", "—")

st.subheader("📉 Liquidation Heatmap (Pair Model1)")
heat = fetch_json("/api/futures/liquidation/heatmap/model1", {"symbol":"BTC"})
st.json(heat if "data" in heat else heat.get("error", heat))
