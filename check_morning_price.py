import requests

url_base = "https://api.bitget.com"
r_t = requests.get(f"{url_base}/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
t_data = r_t['data'][0]
mark_p = float(t_data.get('markPrice', 0))
h24 = float(t_data.get('high24h', 0))
l24 = float(t_data.get('low24h', 0))

r_c1 = requests.get(f"{url_base}/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=1H&limit=8", timeout=5).json()
c1 = r_c1.get('data', [])

print(f"=== MORNING BTC PRICE (11:09 KST): ${mark_p:,.2f} ===")
print(f"24h High: ${h24:,.1f} | 24h Low: ${l24:,.1f}")
print("\nRecent 8 1H Candles (Since 04:00 AM):")
for c in c1[:8]:
    vol = float(c[5])
    o, h, l, cl = float(c[1]), float(c[2]), float(c[3]), float(c[4])
    print(f"  O:${o:,.1f} | H:${h:,.1f} | L:${l:,.1f} | C:${cl:,.1f} | Vol:{vol:.1f} BTC")