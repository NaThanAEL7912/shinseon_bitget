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

async def test_trailing_endpoints():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    
    endpoints = [
        ("/api/v2/mix/order/place-plan-order", {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "marginCoin": "USDT", "planType": "track_plan", "triggerPrice": "80000.0", "rangeRate": "0.00375", "size": "0.7452", "side": "sell", "tradeSide": "close", "orderType": "market"}),
        ("/api/v2/mix/order/place-plan-order", {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "marginCoin": "USDT", "planType": "trailing_stop", "triggerPrice": "80000.0", "rangeRate": "0.00375", "size": "0.7452", "side": "sell", "tradeSide": "close", "orderType": "market"}),
        ("/api/v2/mix/order/place-trailing-stop-order", {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "marginCoin": "USDT", "triggerPrice": "80000.0", "rangeRate": "0.00375", "size": "0.7452", "side": "sell", "tradeSide": "close"}),
        ("/api/v2/mix/order/place-plan-order", {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "marginCoin": "USDT", "planType": "moving_plan", "triggerPrice": "80000.0", "rangeRate": "0.00375", "size": "0.7452", "side": "sell", "tradeSide": "close", "orderType": "market"}),
        ("/api/v2/mix/order/place-plan-order", {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "marginCoin": "USDT", "planType": "pos_loss", "triggerPrice": "80000.0", "size": "0.7452", "side": "sell", "tradeSide": "close", "orderType": "market"})
    ]
    
    async with aiohttp.ClientSession() as session:
        for path, body_dict in endpoints:
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
            async with session.post(url_base + path, headers=headers, data=body_json) as resp:
                res = await resp.json()
                print(f"[{path} | {body_dict.get('planType', 'none')}] Response:", json.dumps(res))

asyncio.run(test_trailing_endpoints())