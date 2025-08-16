import requests
import streamlit as st
import pandas as pd
from datetime import datetime

API_KEY = "a103f20a763d4ad0a39f15aa7bb8d6ec"
BASE = "https://open-api-v4.coinglass.com"
HEADERS = {"CG-API-KEY": API_KEY}

def get_latest_funding(symbol="BTC"):
    url = f"{BASE}/api/futures/funding-rate/exchange-list"
    params = {"symbol": symbol}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()
    if data.get("code") != "0" or not data.get("data"):
        return None
    info = data["data"][0]  # chỉ lấy symbol đầu
    out = []
    for entry in info.get("stablecoin_margin_list", []):
        out.append({
            "Exchange": entry.get("exchange"),
            "Funding Rate": entry.get("funding_rate"),
            "Next Funding (UTC)": datetime.utcfromtimestamp(entry.get("next_funding_time", 0)/1000)
        })
    return pd.DataFrame(out)

st.title("🗓 Coinglass Funding Rate Mới Nhất")

symbol = st.text_input("Symbol (ví dụ: BTC)", "BTC")
if st.button("Get Funding"):
    df = get_latest_funding(symbol)
    if df is None or df.empty:
        st.error("Không có dữ liệu funding rate cho symbol này.")
    else:
        st.dataframe(df)
