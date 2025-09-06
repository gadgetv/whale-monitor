import ccxt
import pandas as pd
import streamlit as st

# ==============================
# 🔗 Kết nối Binance Futures (PUBLIC API, không cần key)
# ==============================
exchange = ccxt.binance({
    "enableRateLimit": True,
    "options": {"defaultType": "future"}
})

# ==============================
# 📌 HÀM TÍNH SUPER TREND
# ==============================
def fetch_supertrend(symbol: str, timeframe="15m", limit=200):
    market = symbol.upper() + "/USDT"
    ohlcv = exchange.fetch_ohlcv(market, timeframe=timeframe, limit=limit)

    df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms")

    # ATR
    df["H-L"] = df["high"] - df["low"]
    df["H-C"] = abs(df["high"] - df["close"].shift())
    df["L-C"] = abs(df["low"] - df["close"].shift())
    df["TR"] = df[["H-L", "H-C", "L-C"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(window=10).mean()

    # Supertrend
    multiplier = 3
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

    last = df.iloc[-1]
    signal = "LONG ✅" if last["close"] > last["ST"] else "SHORT ❌"

    return {
        "coin": market,
        "time": str(last["time"]),
        "close": last["close"],
        "supertrend": last["ST"],
        "signal": signal
    }

# ==============================
# 📌 STREAMLIT APP
# ==============================
st.title("📈 Binance Futures Supertrend Monitor (15m)")

coin = st.text_input("Nhập mã coin (VD: BTC, ETH, BNB):", "BTC")

if st.button("Lấy dữ liệu"):
    try:
        result = fetch_supertrend(coin, timeframe="15m")
        st.success(f"""
        Coin: **{result['coin']}**  
        ⏰ Thời gian: {result['time']}  
        💰 Giá hiện tại: {result['close']}  
        📉 Supertrend: {result['supertrend']}  
        🎯 Entry gần nhất: **{result['signal']}**
        """)
    except Exception as e:
        st.error(f"Lỗi: {e}")
