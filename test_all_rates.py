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

async def test_all_rates():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    path = "/api/v2/mix/order/place-plan-order"
    
    # In Bitget API V2, rangeRate for BTC is usually 0.1 to 5 (e.g. 1 means 1%, 0.5 means 0.5%)
    # Let's test "0.1", "0.2", "0.3", "0.5", "1.0", "2.0", "5.0"
    rates = ["0.1", "0.2", "0.3", "0.5", "1.0", "2.0", "5.0", "0.001", "0.05"]
    
    async with aiohttp.ClientSession() as session:
        for r in rates:
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
                if res.get('code') == '00000':
                    print("SUCCESS WITH RATE:", r, res)
                    break

asyncio.run(test_all_rates())