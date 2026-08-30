import urllib.request, json
url_t = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
req_t = urllib.request.Request(url_t, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_t, timeout=4) as resp:
    t = json.loads(resp.read().decode())
    print(f"[BINANCE LIVE 04:29] Bid: ${t['bidPrice']} | Ask: ${t['askPrice']}")