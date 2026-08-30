import urllib.request, json

def analyze_exhaustion_vs_push():
    try:
        # Binance 1h klines
        url_1h = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=10"
        req_1h = urllib.request.Request(url_1h, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_1h, timeout=5) as resp:
            kl = json.loads(resp.read().decode())
            print("=== [BINANCE 1H CANDLES & VOLUME (PAST 10 HOURS)] ===")
            for k in kl:
                o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
                print(f"1h C: ${c:.1f} | Range: ${h-l:.1f} | Vol: {v:,.1f} BTC")
                
        # Orderbook depth
        url_depth = "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=BTCUSDT"
        req_d = urllib.request.Request(url_depth, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_d, timeout=5) as resp:
            t = json.loads(resp.read().decode())
            print(f"\n[CURRENT LIVE TICKER] Bid: ${t['bidPrice']} | Ask: ${t['askPrice']}")
    except Exception as e:
        print("Err:", e)

analyze_exhaustion_vs_push()