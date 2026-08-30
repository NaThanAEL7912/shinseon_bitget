import urllib.request, json

# Live ticker & depth
url_t = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
req_t = urllib.request.Request(url_t, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_t, timeout=4) as resp:
    t = json.loads(resp.read().decode())

# Recent 15m klines
url_k = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=15m&limit=16"
req_k = urllib.request.Request(url_k, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_k, timeout=4) as resp:
    kl = json.loads(resp.read().decode())

current_price = float(t['bidPrice'])
print(f"[BINANCE LIVE 18:18] Price: ${current_price:,.2f}")

print("\nLast 6 15m Candles (Open, High, Low, Close, Volume):")
for k in kl[-6:]:
    import datetime
    dt = datetime.datetime.fromtimestamp(k[0]/1000)
    print(f" - {dt.strftime('%H:%M')} | O: ${float(k[1]):,.1f} H: ${float(k[2]):,.1f} L: ${float(k[3]):,.1f} C: ${float(k[4]):,.1f} | Vol: {float(k[5]):,.1f} BTC")