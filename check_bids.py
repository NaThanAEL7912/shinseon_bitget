import urllib.request, json
req = urllib.request.Request('https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=BTCUSDT&productType=USDT-FUTURES&limit=50', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    res = json.loads(response.read().decode('utf-8'))
    data = res['data']
    bids = data['bids']
    total_vol_to_74k = sum(float(b[1]) for b in bids if float(b[0]) >= 74000.0)
    print(f'TOTAL_BID_VOLUME_DOWN_TO_74000: {total_vol_to_74k:.2f} BTC')
    print('KEY_BID_WALLS_ABOVE_74000:')
    for b in bids:
        p, v = float(b[0]), float(b[1])
        if v >= 20.0 and p >= 74000.0:
            print(f'  PRICE: {p} | VOL: {v:.2f} BTC')