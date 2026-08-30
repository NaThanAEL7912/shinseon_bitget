import urllib.request, json
req = urllib.request.Request('https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=BTCUSDT&productType=USDT-FUTURES&limit=10', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    res = json.loads(response.read().decode('utf-8'))
    print('--- BITGET ASKS ---')
    for a in res['data']['asks'][:5]:
        print(f'ASK: {a[0]} | VOL: {a[1]}')
    print('--- BITGET BIDS ---')
    for b in res['data']['bids'][:5]:
        print(f'BID: {b[0]} | VOL: {b[1]}')