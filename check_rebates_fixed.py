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

async def get_all_fills(start_ts, end_ts, api_key, secret_key, passphrase):
    url_base = "https://api.bitget.com"
    all_fills = []
    id_less_than = None
    async with aiohttp.ClientSession() as session:
        while True:
            path = f"/api/v2/mix/order/fills?symbol=BTCUSDT&productType=USDT-FUTURES&startTime={start_ts}&endTime={end_ts}&limit=100"
            if id_less_than:
                path += f"&idLessThan={id_less_than}"
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
                'locale': 'ko-KR'
            }
            async with session.get(url_base + path, headers=headers) as resp:
                data = await resp.json()
                f_list = data.get('data', {}).get('fillList', []) if data.get('data') else []
                if not f_list:
                    break
                all_fills.extend(f_list)
                if len(f_list) < 100:
                    break
                id_less_than = f_list[-1].get('tradeId')
                await asyncio.sleep(0.05)
    return all_fills

async def check_rebates_fixed():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    kst = timezone(timedelta(hours=9))
    
    url_base = "https://api.bitget.com"
    path = "/api/v2/mix/order/current-plan?symbol=BTCUSDT&productType=USDT-FUTURES"
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
        'locale': 'ko-KR'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url_base + path, headers=headers) as resp:
            data = await resp.json()
            plans = data.get('data', {}).get('entrustedList', []) if data.get('data') else []
            print("=== [실시간 비트겟 거래소 대기 플랜 주문 (손절/익절 방패)] ===")
            print(f"Total Plans Count: {len(plans)}건")
            for p in plans:
                ptype = p.get('planType')
                trig = float(p.get('triggerPrice', 0))
                size = p.get('size')
                side = p.get('holdSide')
                print(f"- {ptype} | 발동가격: ${trig:,.1f} | 수량: {size} BTC | 방향: {side}")

asyncio.run(check_rebates_fixed())