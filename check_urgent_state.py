import urllib.request, json

def check_urgent_state():
    try:
        url_t = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
        req_t = urllib.request.Request(url_t, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_t, timeout=4) as resp:
            t = json.loads(resp.read().decode())
            print(f"[BINANCE LIVE] Bid: ${t['bidPrice']} | Ask: ${t['askPrice']}")
            
        url_k = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=3"
        req_k = urllib.request.Request(url_k, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_k, timeout=4) as resp:
            kl = json.loads(resp.read().decode())
            for k in kl:
                print(f"1m: O: {float(k[1]):.1f} | H: {float(k[2]):.1f} | L: {float(k[3]):.1f} | C: {float(k[4]):.1f} | Vol: {float(k[5]):.1f}")
    except Exception as e:
        print("Err:", e)

check_urgent_state()