# -*- coding: utf-8 -*-
import requests
import time

# ⚙️ Config
SYMBOL = "BTCUSDT"
INTERVAL = 10  # giây mỗi lần check

def get_funding(symbol):
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
    r = requests.get(url).json()
    return float(r[0]["fundingRate"])

def get_open_interest(symbol):
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    r = requests.get(url).json()
    return float(r["openInterest"])

def get_liquidations(symbol):
    url = f"https://fapi.binance.com/fapi/v1/allForceOrders?symbol={symbol}&limit=5"
    r = requests.get(url).json()
    return r  # trả về list thanh lý gần nhất

# 🔔 Hàm phân tích
def analyze(funding, oi_now, oi_prev, liq_data):
    signal = "SIDEWAY"
    notes = []

    # Funding
    if funding > 0.01:
        notes.append("Funding cao → Retail Long nhiều → dễ DUMP")
        signal = "DUMP"
    elif funding < -0.01:
        notes.append("Funding âm → Retail Short nhiều → dễ PUMP")
        signal = "PUMP"
    else:
        notes.append("Funding trung lập")

    # OI biến động
    if oi_now > oi_prev * 1.02:
        notes.append("OI tăng mạnh → Cá mập gom vị thế")
    elif oi_now < oi_prev * 0.98:
        notes.append("OI giảm → thoát vị thế hoặc sau thanh lý")

    # Thanh lý
    if len(liq_data) > 0:
        side = liq_data[0]["side"]
        notes.append(f"Thanh lý gần nhất: {side}")

    return signal, notes


def main():
    print(f"🐳 Whale Monitor cho {SYMBOL}")
    oi_prev = get_open_interest(SYMBOL)
    time.sleep(1)

    while True:
        try:
            funding = get_funding(SYMBOL)
            oi_now = get_open_interest(SYMBOL)
            liq_data = get_liquidations(SYMBOL)

            signal, notes = analyze(funding, oi_now, oi_prev, liq_data)

            print(f"\n[{time.strftime('%H:%M:%S')}] Funding={funding:.4f}, OI={oi_now}")
            print(f"📊 Dự báo: {signal}")
            for n in notes:
                print("  -", n)

            oi_prev = oi_now
            time.sleep(INTERVAL)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
