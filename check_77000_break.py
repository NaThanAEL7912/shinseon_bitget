import urllib.request, json

def check_77000_break():
    try:
        url_t = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
        req_t = urllib.request.Request(url_t, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_t, timeout=4) as resp:
            t = json.loads(resp.read().decode())
            print(f"[BINANCE LIVE] Bid: ${t['bidPrice']} | Ask: ${t['askPrice']}")
            
        url_d = "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=30"
        req_d = urllib.request.Request(url_d, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_d, timeout=4) as resp:
            d = json.loads(resp.read().decode())
            bids = [[float(p), float(q)] for p, q in d['bids']]
            print("=== [BINANCE BIDS AROUND $77,000] ===")
            for b in bids[:8]:
                print(f"Bid: ${b[0]:.1f} | Qty: {b[1]:.3f} BTC")
    except Exception as e:
        print("Err:", e)

check_77000_break()