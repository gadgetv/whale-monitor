import streamlit as st
import requests
import pandas as pd

API_KEY = "a103f20a763d4ad0a39f15aa7bb8d6ec"
BASE_URL = "https://open-api.coinglass.com/public/v2"

headers = {"coinglassSecret": API_KEY}

def get_funding_rates(symbol="BTC"):
    url = f"{BASE_URL}/funding?symbol={symbol}"
    try:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        
        if "data" in data and data["data"]:
            rates = []
            for item in data["data"]:
                rates.append({
                    "Exchange": item.get("exchangeName"),
                    "FundingRate": item.get("fundingRate", item.get("lastFundingRate", "N/A")),
                    "Time": item.get("time", "N/A")
                })
            return pd.DataFrame(rates)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi lấy funding rate: {e}")
        return pd.DataFrame()

st.title("📊 Whale Monitor - Funding Rates")

symbol = st.text_input("Nhập coin (ví dụ: BTC, ETH):", "BTC")
if st.button("Lấy dữ liệu"):
    df = get_funding_rates(symbol)
    if not df.empty:
        st.dataframe(df)
    else:
        st.warning("Không có dữ liệu funding rate.")
