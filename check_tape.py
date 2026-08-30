import urllib.request, json

def check_tape():
    try:
        url = "https://api.bitget.com/api/v2/mix/market/fills?symbol=BTCUSDT&productType=USDT-FUTURES&limit=20"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            trades = data['data']
            buys = [t for t in trades if t['side'] == 'buy']
            sells = [t for t in trades if t['side'] == 'sell']
            tot_buy_vol = sum(float(t['size']) for t in buys)
            tot_sell_vol = sum(float(t['size']) for t in sells)
            print(f"[LIVE BITGET RECENT 20 TRADES] Buys: {len(buys)} ({tot_buy_vol:.4f} BTC) | Sells: {len(sells)} ({tot_sell_vol:.4f} BTC)")
            print(f"Latest Trade Price: ${trades[0]['price']} | Size: {trades[0]['size']} BTC | Side: {trades[0]['side']}")
    except Exception as e:
        print("Err:", e)

check_tape()