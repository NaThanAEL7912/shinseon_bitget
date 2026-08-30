import urllib.request, json

def check_0100_candle():
    try:
        url_15m = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=15m&limit=4"
        req_15m = urllib.request.Request(url_15m, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_15m, timeout=5) as resp:
            kl = json.loads(resp.read().decode())
            print("=== [BINANCE 15M KLINES - 00:00 ~ 01:00] ===")
            for k in kl:
                o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
                print(f"15m: O: {o:.1f} | H: {h:.1f} | L: {l:.1f} | C: {c:.1f} | Vol: {v:.1f}")
                
        url_t = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
        req_t = urllib.request.Request(url_t, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_t, timeout=5) as resp:
            t = json.loads(resp.read().decode())
            print(f"[CURRENT TICKER] Bid: ${t['bidPrice']} | Ask: ${t['askPrice']}")
    except Exception as e:
        print("Err:", e)

check_0100_candle()