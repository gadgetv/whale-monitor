# app.py
import streamlit as st
import requests
from datetime import datetime, timezone
from dateutil import tz

st.set_page_config(page_title="BTC Dashboard", layout="wide")
st.title("📊 BTC Dashboard — Giá (Mark), OI, Funding, Heatmap")

SYMBOL = "BTCUSDT"
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
BINANCE_OI_URL = "https://fapi.binance.com/fapi/v1/openInterest"
COINGECKO_PRICE = "https://api.coingecko.com/api/v3/simple/price"

# ---------- Helpers ----------
def fetch_json(url, params=None, timeout=8):
    r = requests.get(url, params=params, timeout=timeout)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    try:
        return r.json()
    except Exception as e:
        raise RuntimeError(f"JSON parse error: {e}")

@st.cache_data(ttl=10)
def get_mark_and_funding(symbol=SYMBOL):
    """Lấy markPrice, lastFundingRate, nextFundingTime từ Binance."""
    data = fetch_json(BINANCE_FUNDING_URL, {"symbol": symbol})
    # Trường hợp trả về danh sách thay vì dict (hiếm)
    if isinstance(data, list) and data:
        data = data[0]
    mark = float(data["markPrice"])  # sẽ KeyError nếu payload lỗi -> được catch bên ngoài
    fr = float(data["lastFundingRate"])
    nft_ms = int(data["nextFundingTime"])
    return {"mark_price": mark, "funding_rate": fr, "next_funding_time_ms": nft_ms, "raw": data}

@st.cache_data(ttl=10)
def get_open_interest(symbol=SYMBOL):
    """OI từ Binance Futures (số lượng hợp đồng theo đơn vị base)."""
    data = fetch_json(BINANCE_OI_URL, {"symbol": symbol})
    oi_base = float(data["openInterest"])
    return {"oi_base": oi_base, "raw": data}

@st.cache_data(ttl=10)
def get_price_fallback(vs="usd"):
    """Fallback lấy giá từ CoinGecko phòng khi Binance hỏng."""
    data = fetch_json(COINGECKO_PRICE, {
        "ids": "bitcoin",
        "vs_currencies": vs,
        "include_last_updated_at": "true"
    })
    price = float(data["bitcoin"][vs])
    ts = data["bitcoin"].get("last_updated_at")
    return {"price": price, "ts": ts, "vs": vs, "raw": data}

def ms_to_local_str(ms):
    dt = datetime.fromtimestamp(ms/1000, tz=tz.tzlocal())
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

# ---------- Lấy dữ liệu + chống vỡ ----------
err_msgs = []
mark_price = None
funding_rate = None
next_funding_ms = None
oi_base = None
oi_notional = None

# 1) Mark price + funding
try:
    mf = get_mark_and_funding(SYMBOL)
    mark_price = mf["mark_price"]
    funding_rate = mf["funding_rate"]
    next_funding_ms = mf["next_funding_time_ms"]
except Exception as e:
    err_msgs.append(f"Binance premiumIndex lỗi: {e}")

# 2) OI
try:
    oi = get_open_interest(SYMBOL)
    oi_base = oi["oi_base"]
except Exception as e:
    err_msgs.append(f"Binance openInterest lỗi: {e}")

# 3) Fallback giá nếu mark_price chưa có
fallback_used = False
if mark_price is None:
    try:
        cg = get_price_fallback("usd")
        mark_price = cg["price"]
        fallback_used = True
    except Exception as e:
        err_msgs.append(f"CoinGecko price lỗi (fallback): {e}")

# 4) Tính OI notional (USDT)
if mark_price is not None and oi_base is not None:
    oi_notional = mark_price * oi_base

if err_msgs:
    st.warning("Một số nguồn dữ liệu gặp lỗi. Dashboard vẫn hiển thị phần lấy được.")
    with st.expander("Chi tiết lỗi"):
        for m in err_msgs:
            st.write("•", m)

# ---------- Metrics ----------
col1, col2, col3 = st.columns(3)

if mark_price is not None:
    label = "Mark Price (USDT)"
    if fallback_used:
        label += " — Fallback (CoinGecko)"
    col1.metric(label, f"{mark_price:,.2f} $")
else:
    col1.error("Không lấy được giá.")

if oi_base is not None:
    oi_text = f"{oi_base:,.2f} BTC"
    if oi_notional is not None:
        oi_text += f"  |  ≈ {oi_notional:,.0f} USDT"
    col2.metric("Open Interest (Binance)", oi_text)
else:
    col2.error("Không lấy được OI.")

if funding_rate is not None:
    fr_pct = funding_rate * 100
    sub = ""
    if next_funding_ms:
        sub = f"Next funding: {ms_to_local_str(next_funding_ms)}"
    col3.metric("Funding Rate", f"{fr_pct:.4f} %", help=sub if sub else None)
else:
    col3.error("Không lấy được Funding.")

# ---------- Heatmap ----------
st.header("📉 Liquidation Heatmap")
st.markdown(
    """
    <iframe src="https://www.coinglass.com/LiquidationMap?symbol=BTC"
            width="100%" height="640" frameborder="0"></iframe>
    """,
    unsafe_allow_html=True
)
st.caption("Nếu khung trống do trang chặn nhúng, bấm vào liên kết: https://www.coinglass.com/LiquidationMap?symbol=BTC")

# ---------- Debug dữ liệu thô (tùy chọn) ----------
with st.expander("Dữ liệu thô (debug)"):
    st.write("Nguồn: Binance premiumIndex / openInterest, CoinGecko (fallback).")
    st.write("Mark/Funding:", mf["raw"] if 'mf' in locals() and isinstance(mf, dict) and "raw" in mf else "—")
    st.write("OI:", oi["raw"] if 'oi' in locals() and isinstance(oi, dict) and "raw" in oi else "—")
