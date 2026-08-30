import urllib.request, json

def analyze_77000_dip():
    try:
        # Binance orderbook depth
        url = "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=100"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            bids = [[float(p), float(q)] for p, q in data['bids']]
            asks = [[float(p), float(q)] for p, q in data['asks']]
            
            # Cumulative bids from current to 77000
            bids_77k_775k = [b for b in bids if b[0] >= 77000]
            total_btc_77k = sum(b[1] for b in bids_77k_775k)
            print(f"=== [ORDERBOOK DEPTH DOWN TO $77,000] ===")
            print(f"Total Bids between Current and $77,000: {total_btc_77k:.2f} BTC (Approx ${total_btc_77k*77.4/1000:.1f} Million USD)")
            
            # Major bid blocks
            major_bids = [b for b in bids_77k_775k if b[1] >= 20.0]
            print("Major Bid Walls >= 20 BTC:")
            for b in major_bids[:8]:
                print(f"  Price: ${b[0]:.1f} | Qty: {b[1]:.2f} BTC")
                
        # Moving averages on 15m and 1h
        url_15m = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=15m&limit=30"
        req_15m = urllib.request.Request(url_15m, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_15m, timeout=5) as resp:
            kl_15m = json.loads(resp.read().decode())
            closes_15m = [float(k[4]) for k in kl_15m]
            ma7_15m = sum(closes_15m[-7:]) / 7
            ma25_15m = sum(closes_15m[-25:]) / 25
            print(f"\n15m MA 7: ${ma7_15m:.1f} | 15m MA 25: ${ma25_15m:.1f}")
            
    except Exception as e:
        print("Err:", e)

analyze_77000_dip()