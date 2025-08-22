# -*- coding: utf-8 -*-
import streamlit as st
import requests
from datetime import datetime
from dateutil import tz

st.set_page_config(page_title="TC Futures Dashboard — Binance Only", layout="wide")
st.title("📊 TC Futures Dashboard (Binance Only)")

SYMBOL = st.sidebar.text_input("Symbol (Futures/Spot)", value="BTCUSDT")

SPOT_URL = "https://api.binance.com/api/v3/ticker/price"
PREMIUM_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"          # mark price + funding
OI_NOW_URL = "https://fapi.binance.com/fapi/v1/openInterest"           # current OI (base qty)
OI_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"  # OI history (USD)
LIQ_URL = "https://fapi.binance.com/fapi/v1/allForceOrders"            # recent liquidations

@st.cache_data(ttl=15)
def get_json(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        # Một số lỗi (451…) trả JSON lỗi → vẫn trả r.json để debug
        try:
            data = r.json()
        except Exception:
            data = {"_non_json_text": r.text}
        r.raise_for_status()
        return data, None
    except Exception as e:
        # Trả cả status_code (nếu có) để debug
        code = None
        try:
            code = r.status_code  # noqa
        except Exception:
            pass
        return None, f"{e} | status={code}"

def fmt_ts_ms(ms):
    if not ms:
        return ""
    try:
        return datetime.fromtimestamp(int(ms)/1000, tz=tz.tzlocal()).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return str(ms)

# --------- Lấy dữ liệu ---------
# Spot price
spot, spot_err = get_json(SPOT_URL, {"symbol": SYMBOL})
spot_price = None
if spot and isinstance(spot, dict) and "price" in spot:
    try:
        spot_price = float(spot["price"])
    except Exception:
        spot_price = None

# Mark price + funding (Futures)
prem, prem_err = get_json(PREMIUM_URL, {"symbol": SYMBOL})
mark_price = funding_rate = next_funding_time = None
if prem:
    # Có lúc endpoint trả list nếu không truyền symbol, nhưng ta có symbol nên mong đợi dict
    if isinstance(prem, list) and prem:
        prem = prem[0]
    if isinstance(prem, dict):
        mark_price = float(prem.get("markPrice", 0) or 0)
        try:
            funding_rate = float(prem.get("lastFundingRate", 0) or 0)
        except Exception:
            funding_rate = 0.0
        next_funding_time = prem.get("nextFundingTime")

# OI hiện tại (base qty)
oi_now, oi_now_err = get_json(OI_NOW_URL, {"symbol": SYMBOL})
oi_base_qty = None
if oi_now and isinstance(oi_now, dict) and "openInterest" in oi_now:
    try:
        oi_base_qty = float(oi_now["openInterest"])
    except Exception:
        oi_base_qty = None

# OI history (để có USD value)
oi_hist, oi_hist_err = get_json(OI_HIST_URL, {"symbol": SYMBOL, "period": "5m", "limit": 1})
oi_usd = None
if isinstance(oi_hist, list) and oi_hist:
    last = oi_hist[-1]
    # Trường thường gặp: sumOpenInterest (base), sumOpenInterestValue (USD)
    oi_usd = float(last.get("sumOpenInterestValue", 0) or 0)

# Liquidations (recent)
liq, liq_err = get_json(LIQ_URL, {"symbol": SYMBOL, "limit": 50})

# --------- Hiển thị metrics ---------
col1, col2, col3 = st.columns(3)
col1.metric("Spot Price (USDT)", f"{spot_price:,.2f}" if spot_price else "—")
col2.metric("Mark Price (USDT)", f"{mark_price:,.2f}" if mark_price else "—")
if funding_rate is not None:
    col3.metric("Funding Rate", f"{funding_rate*100:.4f} %")
else:
    col3.metric("Funding Rate", "—")

col4, col5 = st.columns(2)
col4.metric("Open Interest (Base Qty)", f"{oi_base_qty:,.4f}" if oi_base_qty else "—")
col5.metric("Open Interest (USD est.)", f"{oi_usd:,.0f}" if oi_usd else "—")

if next_funding_time:
    st.caption(f"⏰ Next Funding: {fmt_ts_ms(next_funding_time)}")

# --------- Bảng Liquidations ---------
st.subheader("📉 Recent Liquidations (Binance Futures)")
if isinstance(liq, list) and liq:
    # Rút gọn cột chính
    rows = []
    for it in liq:
        rows.append({
            "orderId": it.get("orderId"),
            "side": it.get("side"),
            "price": it.get("price"),
            "qty": it.get("origQty"),
            "quoteQty": it.get("executedQty"),  # không luôn là quote, chỉ minh hoạ
            "time": fmt_ts_ms(it.get("time")),
        })
    import pandas as pd
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
else:
    st.write("Không có dữ liệu hoặc bị chặn.")

# --------- Khu vực Debug ---------
with st.expander("🔧 Debug (raw JSON / lỗi)"):
    st.write("Spot:", spot if spot else spot_err)
    st.write("PremiumIndex:", prem if prem else prem_err)
    st.write("OpenInterest (now):", oi_now if oi_now else oi_now_err)
    st.write("OpenInterestHist:", oi_hist if oi_hist else oi_hist_err)
    st.write("Liquidations:", liq if liq else liq_err)

# --------- Gợi ý nếu bị 451 ---------
def show_451_hint():
    msgs = [spot_err, prem_err, oi_now_err, oi_hist_err, liq_err]
    if any(m and "451" in str(m) for m in msgs):
        st.warning(
            "🔒 Có vẻ máy chủ **Binance** chặn từ môi trường hiện tại (451). "
            "Hãy chạy app **local/VPS** hoặc cấu hình **HTTP(S) proxy**."

        )
show_451_hint()
