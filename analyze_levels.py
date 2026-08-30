import requests

r_ticker = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_ticker['data'][0].get('markPrice', 0))

r_candles = requests.get("https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=1H&limit=48", timeout=5).json()
candles = r_candles.get('data', [])

# Find key levels in the last 48 hours
highs = [float(c[2]) for c in candles]
lows = [float(c[3]) for c in candles]
recent_24h_high = max(highs[:24])
recent_48h_high = max(highs)
recent_24h_low = min(lows[:24])

print(f"Current Mark Price: ${mark_p:,.1f}")
print(f"24h High: ${recent_24h_high:,.1f}")
print(f"48h High: ${recent_48h_high:,.1f}")
print(f"24h Low: ${recent_24h_low:,.1f}")

# Hourly close levels
print("Recent 5 Hourly Highs:", sorted(highs[:10], reverse=True)[:5])