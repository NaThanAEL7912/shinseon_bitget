import requests

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))

r_c1 = requests.get("https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=15m&limit=5", timeout=5).json()
c1 = r_c1.get('data', [])

print(f"Current BTC Price: ${mark_p:,.2f}")
print("\nRecent 5 15m Candles:")
for c in c1[:5]:
    vol = float(c[5])
    o, h, l, cl = float(c[1]), float(c[2]), float(c[3]), float(c[4])
    print(f"  O:${o:,.1f} | H:${h:,.1f} | L:${l:,.1f} | C:${cl:,.1f} | Vol:{vol:.1f} BTC")