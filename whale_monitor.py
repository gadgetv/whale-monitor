import requests

url = "https://api.binance.com/api/v3/ticker/price"
params = {"symbol": "BTCUSDT"}
data = requests.get(url, params=params).json()
print(data)
