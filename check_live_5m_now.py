import urllib.request, json, datetime
req = urllib.request.Request('https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=5m&limit=5', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    res = json.loads(response.read().decode('utf-8'))
    print('--- LIVE 5M CANDLES ---')
    for c in res['data'][:5]:
        t = datetime.datetime.fromtimestamp(int(c[0])/1000).strftime('%H:%M')
        print(f'[{t}] O: {c[1]} | H: {c[2]} | L: {c[3]} | C: {c[4]} | Vol: {c[5]}')