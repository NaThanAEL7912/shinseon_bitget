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

async def check_rebates():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    kst = timezone(timedelta(hours=9))
    start_ts = int(datetime(2026, 8, 19, 0, 0, 0, tzinfo=kst).timestamp() * 1000)
    end_ts = int(datetime(2026, 8, 21, 23, 59, 59, tzinfo=kst).timestamp() * 1000)
    
    # Query account bills (USDT-FUTURES)
    # /api/v2/mix/account/bill
    path = f"/api/v2/mix/account/bill?productType=USDT-FUTURES&coin=USDT&startTime={start_ts}&endTime={end_ts}&limit=100"
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
            print("USDT Futures Bills:")
            if res.get('data') and res['data'].get('bills'):
                for b in res['data']['bills']:
                    c_time = datetime.fromtimestamp(int(b.get('cTime', 0))/1000, tz=kst).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"[{c_time}] Type: {b.get('businessType')} | Amount: {b.get('amount')} | Balance: {b.get('balance')} | Coin: {b.get('coin')}")
            else:
                print("No bills or error:", res)
                
        # Also query spot account bills or rebate records if any
        path_spot = f"/api/v2/spot/account/bills?startTime={start_ts}&endTime={end_ts}&limit=100"
        timestamp = str(int(time.time() * 1000))
        message = timestamp + "GET" + path_spot
        mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        sign = base64.b64encode(mac.digest()).decode('utf-8')
        headers['ACCESS-TIMESTAMP'] = timestamp
        headers['ACCESS-SIGN'] = sign
        async with session.get(url_base + path_spot, headers=headers) as resp:
            res_spot = await resp.json()
            print("\nSpot Bills:")
            if res_spot.get('data') and res_spot['data'].get('bills'):
                for b in res_spot['data']['bills']:
                    c_time = datetime.fromtimestamp(int(b.get('cTime', 0))/1000, tz=kst).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"[{c_time}] GroupType: {b.get('groupType')} | Amount: {b.get('amount')} | Balance: {b.get('balance')} | Coin: {b.get('coin')}")
            else:
                print("No spot bills or:", res_spot)

asyncio.run(check_rebates())