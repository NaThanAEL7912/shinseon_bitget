import urllib.request, json

def inspect_nasdaq_details():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=1m&range=1d"
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
            
            print(f"=== [NASDAQ NQ=F REALTIME 1-MIN] ===")
            print(f"Current: {cur:.2f} | Chg: {cur - prev_close:+.2f} ({((cur - prev_close)/prev_close)*100:+.2f}%)")
            print(f"Day High: {max(highs):.2f} | Day Low: {min(lows):.2f}")
            print("Last 10 1-min Closes:", [round(c, 2) for c in closes[-10:]])
            
            # Check 5m support levels
            recent_low = min(lows[-15:])
            print(f"Recent 15-min Low: {recent_low:.2f}")
    except Exception as e:
        print("Err:", e)

inspect_nasdaq_details()