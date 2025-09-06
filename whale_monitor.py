import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# ===== ⚙️ CONFIG =====
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"

def fetch_klines(symbol: str, interval="15m", limit=200):
    """Lấy dữ liệu nến Futures từ Binance"""
    url = f"{BINANCE_FUTURES_URL}?symbol={symbol.upper()}USDT&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()

    # Chuyển về DataFrame
    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    return df[["time", "open", "high", "low", "close", "volume"]]

def calculate_supertrend(df, period=10, multiplier=3):
    """Tính Supertrend"""
    df["H-L"] = df["high"] - df["low"]
    df["H-C"] = abs(df["high"] - df["close"].shift())
    df["L-C"] = abs(df["low"] - df["close"].shift())
    df["TR"] = df[["H-L", "H-C", "L-C"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(window=period).mean()

    df["Upper Basic"] = (df["high"] + df["low"]) / 2 + multiplier * df["ATR"]
    df["Lower Basic"] = (df["high"] + df["low"]) / 2 - multiplier * df["ATR"]

    df["ST"] = 0.0
    for i in range(1, len(df)):
        if df["close"][i] > df["Upper Basic"][i - 1]:
            df.loc[i, "ST"] = df["Lower Basic"][i]
        elif df["close"][i] < df["Lower Basic"][i - 1]:
            df.loc[i, "ST"] = df["Upper Basic"][i]
        else:
            df.loc[i, "ST"] = df.loc[i - 1, "ST"]

    return df

# ===== 🚀 STREAMLIT APP =====
st.set_page_config(page_title="Binance Futures Supertrend", layout="wide")

st.title("📈 Binance Futures Supertrend Tracker")

coin = st.sidebar.text_input("Nhập mã coin", "BTC").upper()
interval = st.sidebar.selectbox("Chọn khung thời gian", ["15m", "1h", "4h", "1d"], index=0)

if st.sidebar.button("Lấy dữ liệu"):
    try:
        df = fetch_klines(coin, interval=interval, limit=200)
        df = calculate_supertrend(df)

        last = df.iloc[-1]
        signal = "🟢 LONG" if last["close"] > last["ST"] else "🔴 SHORT"

        st.subheader(f"Coin: {coin}USDT ({interval})")
        st.write(f"⏰ Thời gian: {last['time']}")
        st.write(f"💰 Giá hiện tại: {last['close']}")
        st.write(f"📊 Supertrend: {last['ST']}")
        st.success(f"➡️ Entry gần nhất: {signal}")

        st.line_chart(df.set_index("time")[["close", "ST"]])

        with st.expander("Xem dữ liệu chi tiết"):
            st.dataframe(df.tail(20))

    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu: {e}")
