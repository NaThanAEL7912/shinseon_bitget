import requests

# 1. Real-time Ticker & 1m / 5m candles
r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))

r_c1 = requests.get("https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=1m&limit=5", timeout=5).json()
c1 = r_c1.get('data', [])

r_c5 = requests.get("https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=5m&limit=5", timeout=5).json()
c5 = r_c5.get('data', [])

print(f"Current Price: ${mark_p:,.2f}")
print("Recent 3 1-Minute Candles (Open, High, Low, Close, Vol):")
for c in c1[:3]:
    print(f"  O:${float(c[1]):,.1f} | H:${float(c[2]):,.1f} | L:${float(c[3]):,.1f} | C:${float(c[4]):,.1f} | Vol:{float(c[5]):.2f} BTC")

# Check 5m MA support
c5_closes = [float(x[4]) for x in c5]
ma5_5m = sum(c5_closes[:5]) / 5.0
print(f"5m MA5 Close: ${ma5_5m:,.2f}")

entry_p = 77702.1
diff = mark_p - entry_p
print(f"Entry: ${entry_p:,.2f} | Diff: {diff:+.2f} USD")