import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Crypto Price Tracker", layout="wide")

# Hàm lấy dữ liệu từ Binance
def fetch_price(symbol="BTC/USDT"):
    exchange = ccxt.binance()
    ticker = exchange.fetch_ticker(symbol)
    return ticker

# Sidebar nhập coin
coin = st.sidebar.text_input("Nhập mã coin (VD: BTC, ETH, BNB)", "BTC").upper()
symbol = f"{coin}/USDT"

st.title("📊 Theo dõi giá Coin từ Binance")
st.subheader(f"Coin đang theo dõi: {symbol}")

try:
    ticker = fetch_price(symbol)
    st.metric(
        label=f"Giá {symbol}",
        value=f"{ticker['last']:,} USDT",
        delta=f"{ticker['percentage']:.2f}%"
    )

    # Lịch sử dữ liệu (OHLCV)
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=100)
    df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms")

    st.line_chart(df.set_index("time")["close"])

except Exception as e:
    st.error(f"Lỗi: {e}")
