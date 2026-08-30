import urllib.request, json

def inspect_volume_profile():
    try:
        url_5m = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=5m&limit=8"
        req_5m = urllib.request.Request(url_5m, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_5m, timeout=5) as resp:
            kl = json.loads(resp.read().decode())
            print("=== [BINANCE 5M KLINES & VOLUME] ===")
            for k in kl:
                # time, o, h, l, c, vol
                o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
                print(f"5m C: ${c:.1f} | Vol: {v:.1f} BTC")
    except Exception as e:
        print("Err:", e)

inspect_volume_profile()