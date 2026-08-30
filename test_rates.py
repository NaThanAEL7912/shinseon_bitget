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

async def test_rates():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    path = "/api/v2/mix/order/place-plan-order"
    
    test_rates = ["0.01", "0.005", "0.5", "1", "0.4", "0.004", "0.02"]
    
    async with aiohttp.ClientSession() as session:
        for r in test_rates:
            body_dict = {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "marginMode": "isolated",
                "planType": "track_plan",
                "triggerPrice": "80000.0",
                "triggerType": "fill_price",
                "rangeRate": r,
                "size": "0.7452",
                "side": "sell",
                "tradeSide": "close",
                "orderType": "market"
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
            async with session.post(url_base + path, headers=headers, data=body_json) as resp:
                res = await resp.json()
                print(f"[rangeRate: {r}] Response:", json.dumps(res))

asyncio.run(test_rates())