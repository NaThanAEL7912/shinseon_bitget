import asyncio, aiohttp, time, hmac, hashlib, base64, json

with open('/home/ubuntu/server_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

API_KEY = cfg.get('BITGET_API_KEY')
API_SECRET = cfg.get('BITGET_SECRET_KEY')
PASSPHRASE = cfg.get('BITGET_PASSPHRASE')
url_base = 'https://api.bitget.com'
path_plan = '/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES'

def sign(timestamp, method, request_path, body_str):
    message = timestamp + method.upper() + request_path + body_str
    h = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')

async def main():
    async with aiohttp.ClientSession() as session:
        ts = str(int(time.time() * 1000))
        signature = sign(ts, 'GET', path_plan, '')
        headers = {
            'ACCESS-KEY': API_KEY,
            'ACCESS-SIGN': signature,
            'ACCESS-TIMESTAMP': ts,
            'ACCESS-PASSPHRASE': PASSPHRASE,
            'Content-Type': 'application/json',
            'locale': 'ko-KR'
        }
        async with session.get(url_base + path_plan, headers=headers) as resp:
            res_json = await resp.json()
            print(json.dumps(res_json, indent=2, ensure_ascii=False))

asyncio.run(main())