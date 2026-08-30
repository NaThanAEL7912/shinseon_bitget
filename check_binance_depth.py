import urllib.request, json
req = urllib.request.Request('https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=15', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    res = json.loads(response.read().decode('utf-8'))
    print('--- BINANCE ASKS ---')
    for a in res['asks'][:5]:
        print(f'ASK: {a[0]} | VOL: {a[1]}')
    print('--- BINANCE BIDS ---')
    for b in res['bids'][:5]:
        print(f'BID: {b[0]} | VOL: {b[1]}')