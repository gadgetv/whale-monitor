import threading
import queue
import json
import time
import requests
import streamlit as st
from datetime import datetime
from websocket import WebSocketApp

BINANCE_FAPI_BASE = "https://fapi.binance.com"
BINANCE_WS_BASE = "wss://fstream.binance.com/ws"

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]

# Thread-safe queue for liquidation events
_liq_queue = queue.Queue(maxsize=10000)

def ts_to_str(ms):
    try:
        return datetime.utcfromtimestamp(ms/1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""

def get_open_interest(symbol: str):
    # GET /fapi/v1/openInterest
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/openInterest"
    r = requests.get(url, params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    data = r.json()
    # returns: { "openInterest": "12345.678", "symbol": "BTCUSDT", "time": 1589437530011 }
    return float(data.get("openInterest", 0.0)), int(data.get("time", 0))

def get_funding_snapshot(symbol: str):
    # GET /fapi/v1/premiumIndex -> contains lastFundingRate and nextFundingTime
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/premiumIndex"
    r = requests.get(url, params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    data = r.json()
    # fields: lastFundingRate, nextFundingTime, markPrice, indexPrice
    rate = float(data.get("lastFundingRate", 0.0))
    next_time = int(data.get("nextFundingTime", 0))
    mark = float(data.get("markPrice", 0.0))
    index = float(data.get("indexPrice", 0.0))
    return rate, next_time, mark, index

def get_funding_history(symbol: str, limit: int = 50):
    # GET /fapi/v1/fundingRate (ascending order)
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate"
    r = requests.get(url, params={"symbol": symbol, "limit": limit}, timeout=10)
    r.raise_for_status()
    # items: symbol, fundingRate, fundingTime
    return r.json()

def _on_ws_message(_, message: str):
    try:
        data = json.loads(message)
        # Binance liquidation stream snapshot payload has data under "o"
        o = data.get("o") or {}
        # Normalize fields
        event = {
            "E": data.get("E") or int(time.time()*1000),
            "s": o.get("s"),
            "S": o.get("S"),  # side: SELL/BUY
            "o": o.get("o"),  # order type
            "f": o.get("f"),  # avg price
            "ap": o.get("ap"),  # average price
            "q": o.get("q"),  # qty
            "X": o.get("X"),  # order status
            "p": o.get("p"),  # price
        }
        try:
            _liq_queue.put_nowait(event)
        except queue.Full:
            # drop oldest
            try:
                _liq_queue.get_nowait()
                _liq_queue.put_nowait(event)
            except Exception:
                pass
    except Exception:
        pass

def _on_ws_error(_, err):
    # Just log to console; Streamlit UI will show a status.
    print("WebSocket error:", err)

def _on_ws_close(_ws, *_):
    print("WebSocket closed")

def start_liq_ws(symbols):
    # Build a combined stream for multiple symbols:
    # stream format: <symbol>@forceOrder; combined with /stream?streams=...
    streams = "/".join([f"{s.lower()}@forceOrder" for s in symbols])
    url = f"wss://fstream.binance.com/stream?streams={streams}"
    ws_app = WebSocketApp(url, on_message=_on_ws_message, on_error=_on_ws_error, on_close=_on_ws_close)

    def run():
        # Auto-reconnect loop
        while True:
            try:
                ws_app.run_forever(ping_interval=15, ping_timeout=10)
            except Exception as e:
                print("WebSocket run_forever exception:", e)
            time.sleep(3)  # brief backoff then reconnect

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t

# --- Streamlit App ---
st.set_page_config(page_title="OI / Funding / Liquidations Tracker", layout="wide")
st.title("📊 OI / Funding / Liquidations Tracker — Binance")

with st.sidebar:
    st.header("Settings")
    symbols = st.text_input("Symbols (comma-separated, USDⓈ-M Perp)", value=",".join(DEFAULT_SYMBOLS))
    symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    refresh_sec = st.slider("Refresh interval (seconds)", 3, 60, 10, 1)
    show_history = st.checkbox("Show 24 latest funding prints", value=True)
    max_liq_rows = st.number_input("Max liquidation rows to display", min_value=20, max_value=2000, value=200, step=20)
    st.markdown("---")
    st.caption("Data from Binance USDⓈ-M Futures REST/WebSocket APIs.")

# Bootstrap the WS thread exactly once per session (for chosen symbols)
if "ws_symbols" not in st.session_state or st.session_state["ws_symbols"] != tuple(symbols):
    st.session_state["ws_symbols"] = tuple(symbols)
    st.session_state["ws_thread"] = start_liq_ws(symbols)
    # Clear any old queue entries when switching symbols
    with _liq_queue.mutex:
        _liq_queue.queue.clear()

# Top metrics grid
cols = st.columns([2, 1, 1, 1, 1])
cols[0].markdown("### Symbol")
cols[1].markdown("### OI")
cols[2].markdown("### Mark")
cols[3].markdown("### Funding (last)")
cols[4].markdown("### Next Funding")

rows = []
for sym in symbols:
    oi, oi_ts = get_open_interest(sym)
    rate, next_ft, mark, index = get_funding_snapshot(sym)
    rows.append((sym, oi, mark, rate, next_ft, oi_ts))

for i, (sym, oi, mark, rate, next_ft, oi_ts) in enumerate(rows):
    c = st.columns([2, 1, 1, 1, 1])
    c[0].markdown(f"**{sym}**  \n<small>OI time: {ts_to_str(oi_ts)} UTC</small>", unsafe_allow_html=True)
    c[1].markdown(f"{oi:,.0f}")
    c[2].markdown(f"{mark:,.2f}")
    c[3].markdown(f"{rate*100:.4f}%")
    c[4].markdown(f"{ts_to_str(next_ft)} UTC")

st.markdown("---")

# Funding history (optional)
if show_history:
    import pandas as pd
    tabs = st.tabs([f"{s} funding history" for s in symbols])
    for tab, sym in zip(tabs, symbols):
        with tab:
            hist = get_funding_history(sym, limit=24)
            df = pd.DataFrame(hist)
            if not df.empty:
                df["fundingRate"] = df["fundingRate"].astype(float)
                df["fundingTimeStr"] = df["fundingTime"].apply(ts_to_str)
                df = df[["fundingTimeStr", "fundingRate"]].rename(columns={"fundingTimeStr": "Funding Time (UTC)", "fundingRate": "Funding Rate"})
            st.dataframe(df, use_container_width=True)

# Live liquidation tape
st.subheader("🧯 Live Liquidations (Binance forceOrder stream)")
liq_rows = []
try:
    while not _liq_queue.empty() and len(liq_rows) < int(max_liq_rows):
        liq_rows.append(_liq_queue.get_nowait())
except Exception:
    pass

if "liq_buffer" not in st.session_state:
    st.session_state["liq_buffer"] = []

# Append and cap buffer
st.session_state["liq_buffer"][0:0] = liq_rows  # prepend newest
st.session_state["liq_buffer"] = st.session_state["liq_buffer"][: int(max_liq_rows)]

import pandas as pd
df_liq = pd.DataFrame(st.session_state["liq_buffer"])
if not df_liq.empty:
    # map / rename
    df_liq = df_liq.rename(columns={
        "E": "EventTime(UTC)",
        "s": "Symbol",
        "S": "Side",
        "ap": "AvgPrice",
        "q": "Qty",
        "p": "Price",
        "X": "Status",
    })
    if "EventTime(UTC)" in df_liq.columns:
        df_liq["EventTime(UTC)"] = df_liq["EventTime(UTC)"].apply(ts_to_str)
    # Numeric columns
    for col in ["AvgPrice", "Qty", "Price"]:
        if col in df_liq.columns:
            df_liq[col] = pd.to_numeric(df_liq[col], errors="coerce")
    st.dataframe(df_liq[["EventTime(UTC)", "Symbol", "Side", "Qty", "Price", "AvgPrice", "Status"]], use_container_width=True, height=400)
else:
    st.info("Listening for liquidation snapshots... (appears when events occur)")

# Auto-refresh
time.sleep(refresh_sec)
st.rerun()