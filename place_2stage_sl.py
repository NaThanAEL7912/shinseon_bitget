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

async def place_sl_order(session, url_base, api_key, secret_key, passphrase, size, trigger_price):
    path = "/api/v2/mix/order/place-tpsl-order"
    body_dict = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": str(trigger_price),
        "triggerType": "fill_price",
        "size": str(size),
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
        print(f"[SL @ ${trigger_price} / {size} BTC] Response:", json.dumps(res))
        return res

async def main():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    url_base = "https://api.bitget.com"
    
    async with aiohttp.ClientSession() as session:
        # SL 1: 1.0 BTC @ 76200.0
        await place_sl_order(session, url_base, api_key, secret_key, passphrase, "1.0", "76200.0")
        await asyncio.sleep(0.5)
        # SL 2: 1.0 BTC @ 76000.0
        await place_sl_order(session, url_base, api_key, secret_key, passphrase, "1.0", "76000.0")

asyncio.run(main())