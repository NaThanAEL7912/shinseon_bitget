import aiohttp, asyncio, json, hmac, hashlib, base64, time, os
from datetime import datetime, timezone, timedelta

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

async def inspect_raw_fills():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    kst = timezone(timedelta(hours=9))
    start_ts = int(datetime(2026, 8, 20, 0, 0, 0, tzinfo=kst).timestamp() * 1000)
    end_ts = int(datetime(2026, 8, 20, 23, 59, 59, tzinfo=kst).timestamp() * 1000)
    
    path = f"/api/v2/mix/order/fills?symbol=BTCUSDT&productType=USDT-FUTURES&startTime={start_ts}&endTime={end_ts}&limit=10"
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
        async with session.get(url_base + path, headers=headers) as resp:
            res = await resp.json()
            print("Raw fills response sample:")
            if res.get('data') and res['data'].get('fillList'):
                print(json.dumps(res['data']['fillList'][:3], indent=2))
            else:
                print(res)

asyncio.run(inspect_raw_fills())