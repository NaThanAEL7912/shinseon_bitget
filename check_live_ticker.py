import urllib.request, json
url = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=5) as resp:
    data = json.loads(resp.read().decode())
    print(f"[BINANCE LIVE TICKER] Bid: ${data['bidPrice']} | Ask: ${data['askPrice']}")