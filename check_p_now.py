import urllib.request, json
req = urllib.request.Request('https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    res = json.loads(response.read().decode('utf-8'))
    print('BITGET_LIVE_PRICE:', res['data'][0]['lastPr'])