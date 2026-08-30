import urllib.request, json

def check_bounce_0052():
    try:
        url = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=4"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            kl = json.loads(resp.read().decode())
            print("=== [BINANCE 1M KLINES - BOUNCE CONFIRMATION] ===")
            for k in kl:
                o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
                print(f"1M: O: {o:.1f} | H: {h:.1f} | L: {l:.1f} | C: {c:.1f} | Vol: {v:.1f} BTC")
                
        url_t = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
        req_t = urllib.request.Request(url_t, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_t, timeout=5) as resp:
            t = json.loads(resp.read().decode())
            print(f"[CURRENT TICKER] Bid: ${t['bidPrice']} | Ask: ${t['askPrice']}")
    except Exception as e:
        print("Err:", e)

check_bounce_0052()