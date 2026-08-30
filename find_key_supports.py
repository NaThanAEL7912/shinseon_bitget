import urllib.request, json

def find_key_supports():
    try:
        url_1h = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=24"
        req_1h = urllib.request.Request(url_1h, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_1h, timeout=5) as resp:
            kl_1h = json.loads(resp.read().decode())
            print("=== [BINANCE 1H SUPPORT CANDLES - LAST 6] ===")
            for k in kl_1h[-6:]:
                # o, h, l, c
                print(f"1H: O: {float(k[1]):.1f} | H: {float(k[2]):.1f} | L: {float(k[3]):.1f} | C: {float(k[4]):.1f}")
                
        url_t = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
        req_t = urllib.request.Request(url_t, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_t, timeout=5) as resp:
            t = json.loads(resp.read().decode())
            print(f"\n[CURRENT LIVE TICKER] Bid: ${t['bidPrice']} | Ask: ${t['askPrice']}")
    except Exception as e:
        print("Err:", e)

find_key_supports()