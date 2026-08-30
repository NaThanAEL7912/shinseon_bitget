import asyncio, aiohttp, time, hmac, hashlib, base64, json

with open('/home/ubuntu/server_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

API_KEY = cfg.get('BITGET_API_KEY')
API_SECRET = cfg.get('BITGET_SECRET_KEY')
PASSPHRASE = cfg.get('BITGET_PASSPHRASE')
url_base = 'https://api.bitget.com'
path_plan = '/api/v2/mix/order/place-tpsl-order'

orders = [
    {
        'name': '1차 50% 분할익절 (72,400.0)',
        'body': {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'profit_plan',
            'triggerPrice': '72400.0',
            'triggerType': 'fill_price',
            'size': '0.7845',
            'holdSide': 'long'
        }
    },
    {
        'name': '2차 50% 최종익절 (72,800.0)',
        'body': {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'profit_plan',
            'triggerPrice': '72800.0',
            'triggerType': 'fill_price',
            'size': '0.7845',
            'holdSide': 'long'
        }
    }
]

def sign(timestamp, method, request_path, body_str):
    message = timestamp + method.upper() + request_path + body_str
    h = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')

async def main():
    async with aiohttp.ClientSession() as session:
        for ord_info in orders:
            name = ord_info['name']
            body_dict = ord_info['body']
            body_json = json.dumps(body_dict)
            ts = str(int(time.time() * 1000))
            signature = sign(ts, 'POST', path_plan, body_json)
            headers = {
                'ACCESS-KEY': API_KEY,
                'ACCESS-SIGN': signature,
                'ACCESS-TIMESTAMP': ts,
                'ACCESS-PASSPHRASE': PASSPHRASE,
                'Content-Type': 'application/json',
                'locale': 'ko-KR'
            }
            async with session.post(url_base + path_plan, headers=headers, data=body_json) as resp:
                res_text = await resp.text()
                print(f"[{name}] Result: {res_text}")

asyncio.run(main())