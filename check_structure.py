import urllib.request, json

def check_structure():
    try:
        # Binance 5m
        url_bin = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=5m&limit=10"
        req = urllib.request.Request(url_bin, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            klines = json.loads(resp.read().decode())
            print("=== [BINANCE 5M KLINES - LAST 6] ===")
            for k in klines[-6:]:
                # time, open, high, low, close, vol
                o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
                print(f"O: {o:.1f} | H: {h:.1f} | L: {l:.1f} | C: {c:.1f} | Vol: {v:.1f} BTC")
    except Exception as e:
        print("Err:", e)

check_structure()