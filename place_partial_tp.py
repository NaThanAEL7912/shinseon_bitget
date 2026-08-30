import asyncio
import json
import time
import hmac
import hashlib
import base64
import aiohttp

def load_config():
    cfg = {}
    import os
    for fn in ['server_config.json', 'shinseon_config.json', 'client_config.json']:
        if os.path.exists(fn):
            try:
                with open(fn, 'r', encoding='utf-8') as f:
                    cfg.update(json.load(f))
            except Exception:
                pass
    return cfg

async def main():
    config = load_config()
    api_key = config.get('BITGET_API_KEY')
    secret_key = config.get('BITGET_SECRET_KEY')
    passphrase = config.get('BITGET_PASSPHRASE')

    # 비트겟 선물 지정가 분할 익절 (Limit Close / reduceOnly)
    # /api/v2/mix/order/place-order
    url_order = 'https://api.bitget.com/api/v2/mix/order/place-order'
    
    order_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "marginMode": "isolated",
        "size": "0.62",
        "price": "69450.0",
        "side": "sell",
        "orderType": "limit",
        "tradeSide": "close",
        "holdSide": "long",
        "force": "gtc"
    }
    
    body_str = json.dumps(order_body)
    ts = str(int(time.time() * 1000))
    msg = ts + 'POST' + '/api/v2/mix/order/place-order' + body_str
    sig = base64.b64encode(hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sig,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url_order, data=body_str, headers=headers) as resp:
            res = await resp.json()
            print('LIMIT CLOSE TP1 RESULT (69450.0 / 0.62 BTC):', json.dumps(res, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
