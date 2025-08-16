import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Whale Monitor", layout="wide")

st.title("🐳 Whale Monitor - OI, Funding Rate, Liquidations")

# ----- Funding Rate -----
st.subheader("Funding Rate (Binance)")

try:
    url_funding = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
    data_funding = requests.get(url_funding).json()
    st.metric(label="BTCUSDT Funding Rate", 
              value=f"{float(data_funding['lastFundingRate'])*100:.4f}%")
except Exception as e:
    st.error(f"Lỗi funding: {e}")

# ----- Open Interest -----
st.subheader("Open Interest (Coinglass)")

try:
    # Đây chỉ là ví dụ, bạn cần API key từ Coinglass
    url_oi = "https://open-api.coinglass.com/public/v2/openInterest?symbol=BTC"
    headers = {"coinglassSecret": "Y254619f701bf423d9b03f2795ffdd18b"}
    resp = requests.get(url_oi, headers=headers).json()
    df_oi = pd.DataFrame(resp["data"]["openInterestHistory"])
    st.line_chart(df_oi.set_index("time")["sumOpenInterest"])
except Exception as e:
    st.warning("Cần API key Coinglass để lấy OI")

# ----- Liquidation -----
st.subheader("Liquidations (Binance)")

try:
    url_liq = "https://fapi.binance.com/fapi/v1/allForceOrders?symbol=BTCUSDT&limit=10"
    data_liq = requests.get(url_liq).json()
    df_liq = pd.DataFrame(data_liq)
    df_liq["price"] = df_liq["price"].astype(float)
    df_liq["qty"] = df_liq["origQty"].astype(float)
    st.dataframe(df_liq[["time", "side", "price", "qty"]])
except Exception as e:
    st.error(f"Lỗi liquidation: {e}")
