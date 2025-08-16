import threading
import queue
import json
import time
import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from websocket import WebSocketApp

BINANCE_FAPI_BASE = "https://fapi.binance.com"
BINANCE_WS_BASE = "wss://fstream.binance.com/ws"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]

# Thread-safe queue for liquidation events
_liq_queue = queue.Queue(maxsize=20000)

def ts_to_str(ms):
    try:
        return datetime.utcfromtimestamp(ms/1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""

def now_ms():
    return int(time.time() * 1000)

def get_open_interest(symbol: str):
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/openInterest"
    r = requests.get(url, params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    data = r.json()
    return float(data.get("openInterest", 0.0)), int(data.get("time", 0))

def get_funding_snapshot(symbol: str):
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/premiumIndex"
    r = requests.get(url, params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    data = r.json()
    rate = float(data.get("lastFundingRate", 0.0))
    next_time = int(data.get("nextFundingTime", 0))
    mark = float(data.get("markPrice", 0.0))
    index = float(data.get("indexPrice", 0.0))
    return rate, next_time, mark, index

def get_funding_history(symbol: str, limit: int = 24):
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate"
    r = requests.get(url, params={"symbol": symbol, "limit": limit}, timeout=10)
    r.raise_for_status()
    return r.json()

def _on_ws_message(_, message: str):
    try:
        data = json.loads(message)
        o = data.get("o") or {}
        event = {
            "E": data.get("E") or now_ms(),
            "s": o.get("s"),
            "S": o.get("S"),  # SELL/BUY
            "ap": o.get("ap"),
            "q": o.get("q"),
            "p": o.get("p"),
            "X": o.get("X"),
        }
        try:
            _liq_queue.put_nowait(event)
        except queue.Full:
            try:
                _liq_queue.get_nowait()
                _liq_queue.put_nowait(event)
            except Exception:
                pass
    except Exception:
        pass

def _on_ws_error(_, err):
    print("WebSocket error:", err)

def _on_ws_close(_ws, *_):
    print("WebSocket closed")

def start_liq_ws(symbols):
    streams = "/".join([f"{s.lower()}@forceOrder" for s in symbols])
    url = f"wss://fstream.binance.com/stream?streams={streams}"
    ws_app = WebSocketApp(url, on_message=_on_ws_message, on_error=_on_ws_error, on_close=_on_ws_close)

    def run():
        while True:
            try:
                ws_app.run_forever(ping_interval=15, ping_timeout=10)
            except Exception as e:
                print("WebSocket run_forever exception:", e)
            time.sleep(3)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t

# --- Streamlit UI ---
st.set_page_config(page_title="🐳 Whale Monitor — OI/Funding/Liq Alerts", layout="wide")
st.title("🐳 Whale Monitor — OI / Funding / Liquidations (Binance)")

with st.sidebar:
    st.header("Settings")
    symbols = st.text_input("Symbols (comma-separated, USDⓈ-M Perp)", value=",".join(DEFAULT_SYMBOLS))
    symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    refresh_sec = st.slider("Refresh interval (seconds)", 3, 60, 8, 1)
    st.caption("Alert thresholds")
    thr_funding_high = st.number_input("Funding HIGH ≥ (e.g. 0.001 = 0.1%)", min_value=0.0, value=0.001, step=0.0001, format="%.4f")
    thr_funding_low  = st.number_input("Funding LOW ≤ (e.g. -0.0005 = -0.05%)", min_value=-0.01, max_value=0.0, value=-0.0005, step=0.0001, format="%.4f")
    thr_oi_pct_30m   = st.number_input("OI change ≥ |x| in 30m (e.g. 0.05 = 5%)", min_value=0.0, value=0.05, step=0.01, format="%.2f")
    thr_liq_usd_5m   = st.number_input("Single liquidation ≥ USD (5m window)", min_value=100000.0, value=5_000_000.0, step=100000.0, format="%.0f")
    max_liq_rows = st.number_input("Max liquidation rows to display", min_value=50, max_value=5000, value=500, step=50)
    st.markdown("---")
    st.caption("Data: Binance USDⓈ-M REST/WebSocket APIs")

# Bootstrap WS thread when symbols change
if "ws_symbols" not in st.session_state or st.session_state["ws_symbols"] != tuple(symbols):
    st.session_state["ws_symbols"] = tuple(symbols)
    st.session_state["ws_thread"] = start_liq_ws(symbols)
    with _liq_queue.mutex:
        _liq_queue.queue.clear()

# Histories kept in session_state
if "hist" not in st.session_state:
    st.session_state["hist"] = { }  # sym -> DataFrame columns: ts, oi, mark, funding

def append_hist(sym, ts_ms, oi, mark, funding):
    df = st.session_state["hist"].get(sym)
    row = {"ts": ts_ms, "oi": oi, "mark": mark, "funding": funding}
    if df is None or df.empty:
        st.session_state["hist"][sym] = pd.DataFrame([row])
    else:
        st.session_state["hist"][sym] = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    # cap to last 48 hours roughly (assuming refresh ~10s → ~17k rows is fine; we'll cap to 10k rows)
    if len(st.session_state["hist"][sym]) > 10000:
        st.session_state["hist"][sym] = st.session_state["hist"][sym].iloc[-10000:]

def get_hist_ago(sym, minutes: int):
    df = st.session_state["hist"].get(sym)
    if df is None or df.empty:
        return None
    cutoff = now_ms() - minutes*60*1000
    # pick the closest row before/at cutoff
    older = df[df["ts"] <= cutoff]
    if older.empty:
        return None
    return older.iloc[-1]

# Fetch snapshots & build rows
rows = []
for sym in symbols:
    try:
        oi, oi_ts = get_open_interest(sym)
        rate, next_ft, mark, index = get_funding_snapshot(sym)
        append_hist(sym, oi_ts or now_ms(), oi, mark, rate)
        rows.append((sym, oi, mark, rate, next_ft, oi_ts))
    except Exception as e:
        rows.append((sym, float('nan'), float('nan'), float('nan'), 0, 0))

# Top grid
st.subheader("Market Snapshot")
grid = st.columns([2, 1.2, 1.2, 1.2, 2])
grid[0].markdown("**Symbol**")
grid[1].markdown("**OI**")
grid[2].markdown("**Mark**")
grid[3].markdown("**Funding (last)**")
grid[4].markdown("**Next Funding (UTC)**")

for sym, oi, mark, rate, next_ft, oi_ts in rows:
    c = st.columns([2, 1.2, 1.2, 1.2, 2])
    next_str = ts_to_str(next_ft)
    c[0].markdown(f"**{sym}**  \n<small>OI time: {ts_to_str(oi_ts)} UTC</small>", unsafe_allow_html=True)
    c[1].markdown(f"{oi:,.0f}" if pd.notna(oi) else "—")
    c[2].markdown(f"{mark:,.2f}" if pd.notna(mark) else "—")
    c[3].markdown(f"{(rate*100):.4f}%" if pd.notna(rate) else "—")
    c[4].markdown(next_str if next_str else "—")

st.markdown("---")

# Alerts
st.subheader("⚠️ Alerts")
alerts = []

# Drain liq queue and build a local buffer
if "liq_buffer" not in st.session_state:
    st.session_state["liq_buffer"] = []
liq_rows = []
try:
    while not _liq_queue.empty() and len(liq_rows) < int(max_liq_rows):
        liq_rows.append(_liq_queue.get_nowait())
except Exception:
    pass

# prepend newest
st.session_state["liq_buffer"][0:0] = liq_rows
# keep only recent N rows
st.session_state["liq_buffer"] = st.session_state["liq_buffer"][: int(max_liq_rows)]

# Compute alerts per symbol
for sym, oi, mark, rate, next_ft, oi_ts in rows:
    # Funding alerts
    if pd.notna(rate):
        if rate >= thr_funding_high:
            alerts.append((sym, f"Funding HIGH {rate*100:.3f}% ≥ {thr_funding_high*100:.2f}% → nguy cơ long crowded / sập."))
        if rate <= thr_funding_low:
            alerts.append((sym, f"Funding LOW {rate*100:.3f}% ≤ {thr_funding_low*100:.2f}% → short crowded / dễ short squeeze."))
    # OI change 30m
    ref = get_hist_ago(sym, 30)
    if ref is not None and pd.notna(oi) and ref["oi"] > 0:
        chg = (oi - ref["oi"]) / ref["oi"]
        if abs(chg) >= thr_oi_pct_30m:
            direction = "↑" if chg > 0 else "↓"
            alerts.append((sym, f"OI {direction} {chg*100:.2f}% trong 30m → biến động vị thế lớn."))

# Liquidation alerts (>= threshold within last 5m)
now_ms_val = now_ms()
liq5 = []
for ev in st.session_state["liq_buffer"]:
    t = ev.get("E") or now_ms_val
    if t >= now_ms_val - 5*60*1000:
        liq5.append(ev)
liq_big = []
for ev in liq5:
    try:
        price = float(ev.get("p") or ev.get("ap") or 0)
        qty = float(ev.get("q") or 0)
        notional = price * qty
        if notional >= thr_liq_usd_5m:
            liq_big.append((ev.get("s"), ev.get("S"), notional, t))
    except Exception:
        pass
for s, side, notion, _ in liq_big:
    side_txt = "LONG liq" if side == "SELL" else "SHORT liq"  # SELL liquidates long, BUY liquidates short
    alerts.append((s, f"Liquidation lớn ~ ${notion:,.0f} ({side_txt}) trong 5 phút qua."))

# Render alerts
if alerts:
    for sym, msg in alerts[:50]:
        st.warning(f"[{sym}] {msg}")
else:
    st.info("Chưa có alert khớp rule.")

st.markdown("---")

# Charts per symbol
tabs = st.tabs([f"{s} — Charts" for s in symbols])
for tab, sym in zip(tabs, symbols):
    with tab:
        df = st.session_state["hist"].get(sym)
        if df is not None and not df.empty:
            df = df.copy()
            df["time"] = df["ts"].apply(ts_to_str)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Open Interest (rolling)**")
                st.line_chart(df.set_index("time")[["oi"]])
            with c2:
                st.markdown("**Funding (last print)**")
                st.line_chart(df.set_index("time")[["funding"]])
            st.markdown("**Mark Price**")
            st.line_chart(df.set_index("time")[["mark"]])
            # 24 latest funding prints table
            try:
                hist = get_funding_history(sym, 24)
                dff = pd.DataFrame(hist)
                if not dff.empty:
                    dff["fundingRate"] = dff["fundingRate"].astype(float)
                    dff["Funding Time (UTC)"] = dff["fundingTime"].apply(ts_to_str)
                    st.dataframe(dff[["Funding Time (UTC)", "fundingRate"]], use_container_width=True, height=260)
            except Exception:
                pass
        else:
            st.info("Chưa đủ dữ liệu lịch sử. Vui lòng đợi vài chu kỳ refresh.")

st.markdown("---")
st.subheader("🧯 Live Liquidations")
df_liq = pd.DataFrame(st.session_state["liq_buffer"])
if not df_liq.empty:
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
    for col in ["AvgPrice", "Qty", "Price"]:
        if col in df_liq.columns:
            df_liq[col] = pd.to_numeric(df_liq[col], errors="coerce")
    df_liq["NotionalUSD"] = df_liq["Qty"] * df_liq["Price"]
    st.dataframe(df_liq[["EventTime(UTC)", "Symbol", "Side", "Qty", "Price", "AvgPrice", "NotionalUSD", "Status"]], use_container_width=True, height=420)
else:
    st.info("Listening for liquidation snapshots...")

# Auto-refresh
time.sleep(refresh_sec)
st.rerun()