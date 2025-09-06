import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

st.set_page_config(page_title="Binance Futures Supertrend", layout="wide")

# ================== SUPERTREND ==================
def supertrend(df, period=10, multiplier=3):
    df["H-L"] = df["high"] - df["low"]
    df["H-C"] = abs(df["high"] - df["close"].shift())
    df["L-C"] = abs(df["low"] - df["close"].shift())
    df["TR"] = df[["H-L", "H-C", "L-C"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(window=period).mean()

    df["Upper Basic"] = (df["high"] + df["low"]) / 2 + multiplier * df["ATR"]
    df["Lower Basic"] = (df["high"] + df["low"]) / 2 - multiplier * df["ATR"]

    df["ST"] = 0.0
    for i in range(1, len(df)):
        if df["close"][i] > df["Upper Basic"][i-1]:
            df.loc[i, "ST"] = df["Lower Basic"][i]
        elif df["close"][i] < df["Lower Basic"][i-1]:
            df.loc[i, "ST"] = df["Upper Basic"][i]
        else:
            df.loc[i, "ST"] = df.loc[i-1, "ST"]
    return df

# ================== STREAMLIT UI ==================
st.title("📊 Binance Futures Supertrend Tracker")

# Nhập API key
st.sidebar.header("🔑 Binance API Keys")
api_key = st.sidebar.text_input("API Key", type="oL8yT6QFOFSjLwfREVy2aVVUJVqUB4oJSZCPny4JxpHlQjhBizgbEb2N1KhHUSVg")
api_secret = st.sidebar.text_input("API Secret", type="eABiQRYhgRG3uZ2RIMhvz2L0vW9NnnI4JJ7o3xw5mAKXTh2inbB8aQQf6taOFLO")

# Nếu có key thì kết nối
if api_key and api_secret:
    try:
        exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "options": {"defaultType": "future"}
        })

        coin = st.sidebar.text_input("Nhập coin (VD: BTC, ETH, BNB)", "BTC").upper()
        symbol = f"{coin}/USDT"

        timeframe = st.sidebar.selectbox("Chọn khung", ["5m", "15m", "1h", "4h", "1d"], index=1)

        # Lấy dữ liệu
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=200)
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "volume"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")

        # Tính supertrend
        df = supertrend(df)
        last = df.iloc[-1]
        signal = "🟢 LONG" if last["close"] > last["ST"] else "🔴 SHORT"

        # Hiển thị kết quả
        st.subheader(f"Kết quả cho {symbol} ({timeframe})")
        st.metric("Giá hiện tại", f"{last['close']:,} USDT")
        st.metric("Supertrend", f"{last['ST']:.2f}")
        st.metric("Tín hiệu Entry", signal)

        # Hiển thị bảng
        st.dataframe(df.tail(20))

        # Vẽ biểu đồ
        st.line_chart(df.set_index("time")[["close", "ST"]])

    except Exception as e:
        st.error(f"Lỗi khi kết nối Binance: {e}")
else:
    st.warning("👉 Vui lòng nhập API Key & Secret ở sidebar để bắt đầu.")
