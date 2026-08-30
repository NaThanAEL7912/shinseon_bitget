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

async def main():
    env = get_env()
    api_key = env['BITGET_API_KEY']
    secret_key = env['BITGET_SECRET_KEY']
    passphrase = env['BITGET_PASSPHRASE']
    
    path = "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES"
    timestamp = str(int(time.time() * 1000))
    message = timestamp + "GET" + path
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
        async with session.get("https://api.bitget.com" + path, headers=headers) as resp:
            data = await resp.json()
            print("RESP DATA:", json.dumps(data, indent=2))

asyncio.run(main())