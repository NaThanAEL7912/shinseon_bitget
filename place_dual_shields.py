import asyncio, aiohttp, time, json, hmac, hashlib, base64, os

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

async def place_dual_shields():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    path = "/api/v2/mix/order/place-tpsl-order"
    
    orders = [
        {"name": "1차 방패 (50%)", "price": "77420.0", "size": "0.7452"},
        {"name": "2차 최종방패 (50%)", "price": "76850.0", "size": "0.7452"}
    ]
    
    results = []
    async with aiohttp.ClientSession() as session:
        for ord_info in orders:
            body_dict = {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "loss_plan",
                "triggerPrice": ord_info["price"],
                "triggerType": "fill_price",
                "size": ord_info["size"],
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
            async with session.post(url_base + path, headers=headers, data=body_json) as resp:
                res = await resp.json()
                print(f"[{ord_info['name']} @ ${ord_info['price']}] Response:", json.dumps(res))
                results.append((ord_info, res))
    return results

asyncio.run(place_dual_shields())