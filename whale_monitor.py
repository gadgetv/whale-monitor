# app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from dateutil import tz

# ---------- Cài đặt ----------
COINGECKO_SIMPLE_PRICE = "https://api.coingecko.com/api/v3/simple/price"
DEFAULT_PACKAGES_BTC = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]

# ---------- Hàm lấy giá BTC từ CoinGecko ----------
@st.cache_data(ttl=15)  # cache 15s để tránh gọi quá nhiều
def get_btc_price(vs_currency="usd"):
    params = {
        "ids": "bitcoin",
        "vs_currencies": vs_currency,
        "include_last_updated_at": "true"
    }
    try:
        r = requests.get(COINGECKO_SIMPLE_PRICE, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        price = data["bitcoin"][vs_currency]
        ts = data["bitcoin"].get("last_updated_at", None)
        return price, ts, None
    except Exception as e:
        return None, None, str(e)

# ---------- UI ----------
st.set_page_config(page_title="Đơn giá theo gói BTC", layout="wide")
st.title("🪙 Đơn giá theo gói — BTC (Streamlit)")

# Sidebar cấu hình
st.sidebar.header("Cấu hình hiển thị")
currency = st.sidebar.selectbox("Chọn tiền tệ (vs_currency)", options=["usd", "vnd"], index=0)
# Nếu VND, gợi ý: CoinGecko hỗ trợ 'vnd'
use_default_packages = st.sidebar.checkbox("Dùng danh sách gói mặc định", value=True)

if use_default_packages:
    packages = DEFAULT_PACKAGES_BTC
else:
    custom_text = st.sidebar.text_area("Nhập gói BTC (phân cách bằng dấu phẩy). Ví dụ: 0.001,0.01,0.05", value="0.001,0.005,0.01")
    try:
        packages = [float(x.strip()) for x in custom_text.split(",") if x.strip()!=""]
    except:
        packages = DEFAULT_PACKAGES_BTC
        st.sidebar.error("Định dạng gói không hợp lệ. Đã về mặc định.")

# Fee / discount
st.sidebar.header("Phí / chiết khấu")
fee_percent = st.sidebar.number_input("Phí dịch vụ (%)", min_value=0.0, max_value=100.0, value=0.5, step=0.1)
discount_tiers = st.sidebar.text_area("Chiết khấu theo gói (tùy chọn). Format: min_btc:max_percent, ...\nVí dụ: 0.5:2,1:3 (nếu mua >=0.5 BTC giảm 2%, >=1 giảm 3%)", value="0.5:2,1:3")

# Parse discount tiers
def parse_discount(s: str):
    out = []
    try:
        s = s.strip()
        if not s:
            return out
        parts = [p.strip() for p in s.split(",") if p.strip()]
        for p in parts:
            a,b = p.split(":")
            out.append((float(a.strip()), float(b.strip())))
        # sort by threshold ascending
        out.sort(key=lambda x: x[0])
    except Exception:
        out = []
    return out

discounts = parse_discount(discount_tiers)

# Lấy giá BTC
price, ts, err = get_btc_price(vs_currency=currency)
if err:
    st.error(f"Lỗi khi lấy giá từ CoinGecko: {err}")
    st.stop()

# Hiển thị giá
col1, col2 = st.columns([2,1])
with col1:
    st.metric(label=f"Giá Bitcoin (1 BTC) — {currency.upper()}", value=f"{price:,.2f}")
    if ts:
        # convert timestamp to local timezone display
        dt = datetime.fromtimestamp(int(ts), tz=tz.tzlocal())
        st.caption(f"Cập nhật: {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
with col2:
    st.write("Tùy chọn")
    st.write(f"Số gói: {len(packages)}")
    st.write(f"Phí: {fee_percent:.2f}%")

# Tạo bảng tính
rows = []
for amt in packages:
    base_total = amt * price
    # tìm chiết khấu theo tiers: áp dụng mức lớn nhất mà amt >= threshold
    applied_discount = 0.0
    for threshold, disc_percent in discounts:
        if amt >= threshold:
            applied_discount = disc_percent
    # tính tiền sau discount (giảm %)
    after_discount = base_total * (1 - applied_discount/100.0)
    # cộng phí (phí tính trên số tiền sau giảm)
    fee_amount = after_discount * (fee_percent/100.0)
    final_total = after_discount + fee_amount
    rows.append({
        "BTC": amt,
        f"Giá 1 BTC ({currency.upper()})": price,
        "Tiền gốc": base_total,
        "Chiết khấu (%)": applied_discount,
        "Sau chiết khấu": after_discount,
        "Phí (%)": fee_percent,
        "Phí (số tiền)": fee_amount,
        "Tổng phải trả": final_total
    })

df = pd.DataFrame(rows)
# format số với dấu phẩy
pd.options.display.float_format = '{:,.2f}'.format

st.header("Bảng đơn giá theo gói")
st.dataframe(df.style.format("{:,.2f}"))

# Cho phép xuất CSV
csv = df.to_csv(index=False)
st.download_button("Tải CSV", data=csv, file_name=f"btc_packages_{currency}.csv", mime="text/csv")

# Biểu đồ đơn giản
st.header("Biểu đồ — Tổng phải trả theo gói")
try:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(df["BTC"], df["Tổng phải trả"], marker="o")
    ax.set_xlabel("BTC")
    ax.set_ylabel(f"Tổng ({currency.upper()})")
    ax.set_title("Tổng phải trả theo từng gói BTC")
    ax.grid(True)
    st.pyplot(fig)
except Exception as e:
    st.write("Không thể vẽ biểu đồ:", e)

# Thông báo / chú thích
st.markdown("""
**Ghi chú**
- Giá lấy từ CoinGecko (endpoint `simple/price`). Cập nhật mỗi lần chạy / cache 15 giây.
- Bạn có thể chỉnh `Phí (%)` và `Chiết khấu theo gói` ở bên trái.
- Đơn vị tiền tệ: `usd` hoặc `vnd` (CoinGecko hỗ trợ cả hai).
""")
