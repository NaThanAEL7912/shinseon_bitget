import aiohttp, asyncio, json, hmac, hashlib, base64, time, os

def get_env():
    env = {}
    if os.path.exists('/home/ubuntu/.env'):
        with open('/home/ubuntu/.env', 'r') as f:
            for l in f:
                if '=' in l and not l.startswith('#'):
                    k, v = l.strip().split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get('BITGET_API_KEY') and os.path.exists('/home/ubuntu/server_config.json'):
        with open('/home/ubuntu/server_config.json', 'r') as f:
            cfg = json.load(f)
            env['BITGET_API_KEY'] = cfg.get('BITGET_API_KEY') or cfg.get('api_key')
            env['BITGET_SECRET_KEY'] = cfg.get('BITGET_SECRET_KEY') or cfg.get('secret_key') or cfg.get('secret')
            env['BITGET_PASSPHRASE'] = cfg.get('BITGET_PASSPHRASE') or cfg.get('passphrase')
    return env

async def test_trailing():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    
    # Check Bitget V2 Plan Orders / Trailing Stop endpoints
    # 1. /api/v2/mix/order/place-tpsl-order with planType: 'track_plan' or similar
    # In Bitget V2 API, Trailing Stop is planType='track_plan' with triggerPrice, rangeRate (e.g. '0.00375' or '0.004')
    
    # Let's test track_plan endpoint structure
    path = "/api/v2/mix/order/place-tpsl-order"
    body_dict = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "track_plan",
        "triggerPrice": "80000.0",
        "triggerType": "fill_price",
        "rangeRate": "0.00375", # 300 / 80000 = 0.375%
        "size": "0.7452",
        "holdSide": "long"
    }
    body_json = json.dumps(body_dict)
    timestamp = str(int(time.time() * 1000))
    message = timestamp + "POST" + path + body_json
    mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url_base + path, headers=headers, data=body_json) as resp:
            res = await resp.json()
            print("Track plan response:", json.dumps(res))

asyncio.run(test_trailing())