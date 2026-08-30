import urllib.request, json

def inspect_nasdaq_5m():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=5m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            quote = data['chart']['result'][0]['indicators']['quote'][0]
            opens = [p for p in quote['open'] if p is not None]
            highs = [p for p in quote['high'] if p is not None]
            lows = [p for p in quote['low'] if p is not None]
            closes = [p for p in quote['close'] if p is not None]
            meta = data['chart']['result'][0]['meta']
            prev_close = meta.get('chartPreviousClose')
            cur = closes[-1]
            
            print(f"=== [NASDAQ NQ=F 5-MIN CANDLES - LAST 6] ===")
            print(f"Current: {cur:.2f} | Chg: {cur - prev_close:+.2f} ({((cur - prev_close)/prev_close)*100:+.2f}%)")
            for i in range(-6, 0):
                chg_c = closes[i] - opens[i]
                print(f"O: {opens[i]:.2f} | H: {highs[i]:.2f} | L: {lows[i]:.2f} | C: {closes[i]:.2f} | Body: {chg_c:+.2f} pt")
    except Exception as e:
        print("Err:", e)

inspect_nasdaq_5m()