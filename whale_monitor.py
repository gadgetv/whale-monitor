import time
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

BINANCE_OI_URL = "https://www.binance.com/futures/data/openInterestHist"
BINANCE_FUTURES_PRICE = "https://fapi.binance.com/fapi/v1/ticker/price"

def fetch_json(url, params):
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        return None
    return None

def get_open_interest(symbol, period="5m"):
    data = fetch_json(BINANCE_OI_URL, {"symbol": symbol, "period": period, "limit": 2})
    if not data or len(data) < 2:
        return None
    prev, curr = data[-2], data[-1]
    oi_prev = float(prev.get("sumOpenInterest", prev.get("openInterest", 0)))
    oi_curr = float(curr.get("sumOpenInterest", curr.get("openInterest", 0)))
    ts_prev = int(prev.get("timestamp", prev.get("time", 0)))
    ts_curr = int(curr.get("timestamp", curr.get("time", 0)))
    return {
        "symbol": symbol,
        "oi_prev": oi_prev,
        "oi_curr": oi_curr,
        "pct_change": (oi_curr - oi_prev) / oi_prev * 100 if oi_prev else 0,
        "time_prev": datetime.utcfromtimestamp(ts_prev/1000).strftime("%Y-%m-%d %H:%M"),
        "time_curr": datetime.utcfromtimestamp(ts_curr/1000).strftime("%Y-%m-%d %H:%M")
    }

def get_price(symbol):
    d = fetch_json(BINANCE_FUTURES_PRICE, {"symbol": symbol})
    if isinstance(d, dict) and "price" in d:
        return float(d["price"])
    return None

# --- Streamlit UI ---
st.set_page_config(page_title="Binance OI Monitor", layout="wide")
st.title("📊 Binance Futures OI Monitor")

with st.sidebar:
    st.header("⚙️ Settings")
    symbols = st.text_input("Symbols (comma-separated)", "BTCUSDT,ETHUSDT,SOLUSDT").upper().replace(" ", "").split(",")
    period = st.selectbox("Period", ["5m","15m","30m","1h","4h","1d"], index=0)
    threshold = st.number_input("Alert threshold %", value=3.0, step=0.5)
    refresh = st.number_input("Refresh interval (seconds)", value=60, step=10)

st.write(f"### Monitoring {symbols} | Period={period} | Threshold={threshold}%")

results = []
for sym in symbols:
    info = get_open_interest(sym, period)
    if not info:
        continue
    price = get_price(sym)
    notional_move = None
    if price:
        notional_move = (info["oi_curr"] - info["oi_prev"]) * price
    row = {
        "Symbol": sym,
        "OI Prev": info["oi_prev"],
        "OI Curr": info["oi_curr"],
        "Δ%": round(info["pct_change"], 2),
        "Time": f"{info['time_prev']} → {info['time_curr']}",
        "≈ Notional Move (USDT)": f"{notional_move:,.0f}" if notional_move else ""
    }
    results.append(row)

if results:
    df = pd.DataFrame(results)
    def highlight(val):
        try:
            if float(val) >= threshold:
                return "background-color: lightgreen; font-weight: bold"
            elif float(val) <= -threshold:
                return "background-color: pink; font-weight: bold"
        except:
            return ""
        return ""
    st.dataframe(df.style.applymap(highlight, subset=["Δ%"]))
else:
    st.warning("⚠️ Không lấy được dữ liệu OI, thử lại...")

# Auto-refresh
st_autorefresh = st.empty()
st_autorefresh.text(f"Page refreshes every {refresh} sec...")
time.sleep(refresh)
st.experimental_rerun()
