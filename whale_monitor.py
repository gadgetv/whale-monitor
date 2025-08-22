import streamlit as st
import requests
from datetime import datetime
from dateutil import tz

# Thay YOUR_KEY bằng API key Coinglass của bạn
API_KEY = "YOUR_KEY"
HEADERS = {"coinglassSecret": API_KEY}
BASE = "https://open-api-v4.coinglass.com"

st.set_page_config(page_title="TC Futures Dashboard (Coinglass API)", layout="wide")
st.title("📊 TC Futures Dashboard (Coinglass API)")

def fetch_json(path, params=None):
    try:
        resp = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Lỗi API {path}: {e}")
        return {}

# 1. Spot Price via Coinglass: dùng price OHLC history, lấy phần tử mới nhất
spot_j = fetch_json("/api/price/ohlc-history", {"symbol": "BTC", "interval": "1m", "limit": 1})
spot_price = None
if spot_j.get("data"):
    last = spot_j["data"][-1]
    spot_price = float(last.get("close", 0))

# 2. Open Interest (aggregate across exchanges)
oi_j = fetch_json("/api/futures/open-interest/exchange-list", {"symbol": "BTC"})
oi_usd = oi_j.get("data", [{}])[0].get("open_interest_usd", None)

# 3. Funding Rate (Binance stablecoin-margin)
fr_j = fetch_json("/api/futures/funding-rate/exchange-list", {"symbol": "BTC"})
fr_list = fr_j.get("data", [{}])[0].get("stablecoin_margin_list", [])
fr_rate = None; fr_next = None
for f in fr_list:
    if f.get("exchange") == "Binance":
        fr_rate = f.get("funding_rate")
        fr_next = f.get("next_funding_time")
        break

# Display Metrics
col1, col2, col3 = st.columns(3)
col1.metric("BTC Spot Price", f"{spot_price:,.2f} USDT" if spot_price else "—")
col2.metric("Open Interest (Total USD)", f"{oi_usd:,.0f}" if oi_usd else "—")
if fr_rate is not None:
    dt = datetime.fromtimestamp(fr_next/1000, tz=tz.tzlocal()) if fr_next else ""
    col3.metric("Funding Rate (Binance)", f"{fr_rate*100:.4f} %", delta=None, help=f"Next: {dt}")
else:
    col3.metric("Funding Rate (Binance)", "—")

# 4. Liquidation Heatmap
st.subheader("📉 Liquidation Heatmap (Pair model1)")
hm_j = fetch_json("/api/futures/liquidation/heatmap/model1", {"symbol": "BTC"})
st.json(hm_j)
