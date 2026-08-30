import urllib.request, json

def check_tech_macro():
    try:
        # Check Nasdaq & Tech giants (NVDA, AAPL, MSFT, AMD)
        tickers = ['NQ=F', 'NVDA', 'AAPL', 'MSFT', 'AMD', 'COIN']
        for t in tickers:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range=1d"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode())
                    meta = data['chart']['result'][0]['meta']
                    price = meta.get('regularMarketPrice')
                    prev = meta.get('chartPreviousClose')
                    chg = price - prev
                    pct = (chg / prev) * 100
                    print(f"[{t:5s}] Price: ${price:,.2f} | Chg: {chg:+,.2f} ({pct:+.2f}%)")
            except Exception as e:
                print(f"[{t:5s}] Err: {e}")
    except Exception as e:
        print("General Err:", e)

check_tech_macro()