import urllib.request, json

def check_all():
    try:
        # 1. Nasdaq
        url_nq = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=1m&range=1d"
        req_nq = urllib.request.Request(url_nq, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_nq, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            meta = data['chart']['result'][0]['meta']
            quote = data['chart']['result'][0]['indicators']['quote'][0]
            close_prices = [p for p in quote['close'] if p is not None]
            cur_nq = meta.get('regularMarketPrice') or close_prices[-1]
            prev_close = meta.get('chartPreviousClose')
            chg = cur_nq - prev_close
            chg_pct = (chg / prev_close) * 100
            print(f"[LIVE NASDAQ NQ=F] Cur: {cur_nq:.2f} | Chg: {chg:+.2f} ({chg_pct:+.2f}%) | Last 5 mins: {close_prices[-5:]}")
            
        # 2. Bitcoin Bitget
        url_btc = "https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES"
        req_btc = urllib.request.Request(url_btc, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_btc, timeout=5) as resp:
            data_btc = json.loads(resp.read().decode())
            last_btc = data_btc['data'][0]['lastPr']
            print(f"[LIVE BITGET BTC] Cur: ${last_btc}")
    except Exception as e:
        print("Err:", e)

check_all()