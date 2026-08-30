import urllib.request, json

def check_nasdaq_trend():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=15m&range=5d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            quote = data['chart']['result'][0]['indicators']['quote'][0]
            closes = [p for p in quote['close'] if p is not None]
            highs = [p for p in quote['high'] if p is not None]
            lows = [p for p in quote['low'] if p is not None]
            meta = data['chart']['result'][0]['meta']
            cur = closes[-1]
            prev_close = meta.get('chartPreviousClose')
            
            print(f"=== [NASDAQ NQ=F 15-MIN MULTI-DAY STRUCTURE] ===")
            print(f"Current: {cur:.2f} | Chg: {cur - prev_close:+.2f} ({((cur - prev_close)/prev_close)*100:+.2f}%)")
            print(f"5-Day High: {max(highs):.2f} | 5-Day Low: {min(lows):.2f}")
            print("Last 8 15-min Closes:", [round(c, 2) for c in closes[-8:]])
            
            # Check Daily Support
            day_open = closes[-30] if len(closes) >= 30 else closes[0]
            print(f"Session Trend Analysis: Cur({cur:.1f}) vs Day Open({day_open:.1f})")
    except Exception as e:
        print("Err:", e)

check_nasdaq_trend()