import urllib.request, json

def check_sr():
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"[BINANCE BIDS/ASKS] Bid: ${data['bidPrice']} ({data['bidQty']} BTC) | Ask: ${data['askPrice']} ({data['askQty']} BTC)")
            
        url_k = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=5"
        req_k = urllib.request.Request(url_k, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_k, timeout=5) as resp:
            kl = json.loads(resp.read().decode())
            print("=== [RECENT 1M KLINES] ===")
            for k in kl:
                print(f"O: {float(k[1]):.1f} | H: {float(k[2]):.1f} | L: {float(k[3]):.1f} | C: {float(k[4]):.1f} | Vol: {float(k[5]):.1f} BTC")
    except Exception as e:
        print("Err:", e)

check_sr()