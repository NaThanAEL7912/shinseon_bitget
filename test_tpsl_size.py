# -*- coding: utf-8 -*-
import asyncio, json, time, hmac, hashlib, base64, aiohttp

def load_cfg():
    with open('/home/ubuntu/server_config.json', 'r') as f:
        return json.load(f)

async def test_tpsl_size():
    cfg = load_cfg()
    api_key = cfg.get('BITGET_API_KEY')
    secret_key = cfg.get('BITGET_SECRET_KEY')
    passphrase = cfg.get('BITGET_PASSPHRASE')
    
    url_base = 'https://api.bitget.com'
    path = '/api/v2/mix/order/place-tpsl-order'
    
    tp_body = {
        'symbol': 'BTCUSDT',
        'productType': 'USDT-FUTURES',
        'marginCoin': 'USDT',
        'planType': 'pos_profit',
        'triggerPrice': '63994.0',
        'triggerType': 'fill_price',
        'size': '0.0005',
        'holdSide': 'long'
    }
    
    b_json = json.dumps(tp_body)
    ts = str(int(time.time() * 1000))
    msg = ts + 'POST' + path + b_json
    mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign, 'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url_base + path, headers=headers, data=b_json) as resp:
            res = await resp.json()
            print('TP size RES:', res)

asyncio.run(test_tpsl_size())
