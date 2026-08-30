import asyncio, aiohttp, time, json, hmac, hashlib, base64, os

def get_env():
    env = {}
    if os.path.exists('/home/ubuntu/server_config.json'):
        with open('/home/ubuntu/server_config.json', 'r') as f:
            cfg = json.load(f)
            env['BITGET_API_KEY'] = cfg.get('BITGET_API_KEY') or cfg.get('api_key')
            env['BITGET_SECRET_KEY'] = cfg.get('BITGET_SECRET_KEY') or cfg.get('secret_key') or cfg.get('secret')
            env['BITGET_PASSPHRASE'] = cfg.get('BITGET_PASSPHRASE') or cfg.get('passphrase')
    return env

async def place_sl_order(session, api_key, secret_key, passphrase, size, trigger_price):
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
    
    url = "https://api.bitget.com" + path
    async with session.post(url, data=body_json, headers=headers) as resp:
        res = await resp.json()
        print(f"[{trigger_price} SL RESULT]:", json.dumps(res, indent=2))
        return res

async def main():
    env = get_env()
    api_key = env['BITGET_API_KEY']
    secret_key = env['BITGET_SECRET_KEY']
    passphrase = env['BITGET_PASSPHRASE']
    
    async with aiohttp.ClientSession() as session:
        # Order 1: 50% (1.8339 BTC) @ 77100.0
        r1 = await place_sl_order(session, api_key, secret_key, passphrase, "1.8339", "77100.0")
        # Order 2: 50% (1.8340 BTC) @ 76900.0
        r2 = await place_sl_order(session, api_key, secret_key, passphrase, "1.8340", "76900.0")

if __name__ == "__main__":
    asyncio.run(main())