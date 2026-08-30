import urllib.request, json
from datetime import datetime

url = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=20"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=5)
data = json.loads(resp.read().decode('utf-8'))

print("=== BTCUSDT 1m Kline (Last 20 minutes) ===")
for k in data:
    ts = k[0] / 1000.0
    dt_str = datetime.fromtimestamp(ts).strftime('%H:%M')
    op, hi, lo, cl, vol = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
    print(f"[{dt_str}] Open: {op:,.1f} | High: {hi:,.1f} | Low: {lo:,.1f} | Close: {cl:,.1f} | Vol: {vol:,.1f}")