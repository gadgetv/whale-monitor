# whale_dashboard.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

st.set_page_config(page_title="Whale Monitor", layout="wide")

# --- Sidebar ---
st.sidebar.title("🐋 Whale Monitor Dashboard")
symbol = st.sidebar.selectbox("Chọn cặp coin", ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
interval = st.sidebar.selectbox("Khung thời gian", ["1h", "4h", "12h", "1d"])

# --- Funding Rate ---
st.subheader("📊 Funding Rate")
url_funding = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=50"
funding_data = requests.get(url_funding).json()
df_funding = pd.DataFrame(funding_data)
df_funding["fundingTime"] = pd.to_datetime(df_funding["fundingTime"], unit="ms")
fig_funding = px.line(df_funding, x="fundingTime", y="fundingRate", title=f"{symbol} Funding Rate")
st.plotly_chart(fig_funding, use_container_width=True)

# --- Open Interest ---
st.subheader("📈 Open Interest (OI)")
url_oi = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period={interval}&limit=50"
oi_data = requests.get(url_oi).json()
df_oi = pd.DataFrame(oi_data)
df_oi["timestamp"] = pd.to_datetime(df_oi["timestamp"], unit="ms")
fig_oi = px.line(df_oi, x="timestamp", y="sumOpenInterest", title=f"{symbol} Open Interest")
st.plotly_chart(fig_oi, use_container_width=True)

# --- Volume ---
st.subheader("💹 Trading Volume")
url_klines = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=100"
klines = requests.get(url_klines).json()
df_vol = pd.DataFrame(klines, columns=["time","o","h","l","c","v","close_time","qv","trades","tb","tq","ignore"])
df_vol["time"] = pd.to_datetime(df_vol["time"], unit="ms")
fig_vol = px.bar(df_vol, x="time", y="v", title=f"{symbol} Futures Volume")
st.plotly_chart(fig_vol, use_container_width=True)

# --- Liquidation Heatmap (demo) ---
st.subheader("🔥 Liquidation Heatmap (Demo)")
st.info("API heatmap từ Coinglass/Hyblock cần API key riêng. Ở đây demo bằng Volume clusters.")
fig_heat = px.density_heatmap(df_vol, x="time", y="c", z="v", nbinsx=20, nbinsy=20, title="Liquidation Heatmap (proxy)")
st.plotly_chart(fig_heat, use_container_width=True)

# --- Tin tức ---
st.subheader("📰 Tin tức Crypto")
news_url = "https://cryptopanic.com/api/v1/posts/?auth_token=YOUR_TOKEN&public=true"
try:
    news = requests.get(news_url).json()
    for n in news["results"][:5]:
        st.markdown(f"- [{n['title']}]({n['url']})")
except:
    st.warning("Không load được tin tức (cần API key CryptoPanic).")
