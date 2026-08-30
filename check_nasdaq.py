import urllib.request, json

def get_nasdaq():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=5m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            meta = data['chart']['result'][0]['meta']
            quote = data['chart']['result'][0]['indicators']['quote'][0]
            close_prices = [p for p in quote['close'] if p is not None]
            cur_price = meta.get('regularMarketPrice') or close_prices[-1]
            prev_close = meta.get('chartPreviousClose')
            chg = cur_price - prev_close
            chg_pct = (chg / prev_close) * 100
            print(f"[NASDAQ NQ=F FUTURES] Cur: {cur_price:.2f} | Chg: {chg:+.2f} ({chg_pct:+.2f}%) | Recent 5m: {close_prices[-5:]}")
    except Exception as e:
        print("Yahoo Err:", e)

get_nasdaq()