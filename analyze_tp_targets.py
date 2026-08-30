import urllib.request, json

# 1. 15m & 1h Klines
url_15m = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=15m&limit=100"
req = urllib.request.Request(url_15m, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=5) as resp:
    k15 = json.loads(resp.read().decode())

url_1h = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=100"
req_1h = urllib.request.Request(url_1h, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_1h, timeout=5) as resp:
    k1h = json.loads(resp.read().decode())

# 2. Orderbook Depth
url_depth = "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=100"
req_d = urllib.request.Request(url_depth, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_d, timeout=5) as resp:
    depth = json.loads(resp.read().decode())

current_price = float(k15[-1][4])
high_24h = max(float(k[2]) for k in k15[-96:])
low_24h = min(float(k[3]) for k in k15[-96:])

# High resistances in 15m/1h
recent_highs = sorted([float(k[2]) for k in k15[-30:]], reverse=True)
asks = [(float(p), float(q)) for p, q in depth['asks']]

# Find major sell walls
large_walls = [a for a in asks if a[1] >= 15.0 or (a[0] % 500 == 0 and a[1] >= 5.0)]

print(f"CURRENT PRICE: ${current_price:,.2f}")
print(f"24h Range: ${low_24h:,.1f} ~ ${high_24h:,.1f}")
print("\nRecent 15m Swing Highs:")
for h in set(recent_highs[:10]):
    print(f" - Resistance: ${h:,.1f}")

print("\nMajor Ask Walls above current price:")
for p, q in large_walls[:8]:
    print(f" - ${p:,.1f} : {q:.3f} BTC (${p*q:,.0f})")