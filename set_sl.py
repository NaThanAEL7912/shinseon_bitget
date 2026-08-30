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

    path_pos = '/api/v2/mix/position/single-position'
    ts = str(int(time.time() * 1000))
    params = 'symbol=BTCUSDT&productType=USDT-FUTURES&marginCoin=USDT'
    msg = ts + 'GET' + path_pos + '?' + params
    sig = base64.b64encode(hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sig,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase,
        'locale': 'en-US'
    }

    async with aiohttp.ClientSession() as session:
        # 1. 포지션 수량 조회
        total_qty = '1.0'
        async with session.get('https://api.bitget.com' + path_pos + '?' + params, headers=headers) as resp:
            data = await resp.json()
            print('POSITION DATA:', json.dumps(data, indent=2))
            pos_list = data.get('data', [])
            for p in pos_list:
                if p.get('holdSide') == 'long' and float(p.get('total', 0)) > 0:
                    total_qty = str(p.get('total'))
        
        print(f'==> SETTING STOP-LOSS FOR {total_qty} BTC AT 68100.0')

        # 2. SL 발주 (pos_loss)
        sl_body = {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'pos_loss',
            'triggerPrice': '68100.0',
            'triggerType': 'mark_price',
            'size': total_qty,
            'holdSide': 'long'
        }
        body_str = json.dumps(sl_body)
        ts2 = str(int(time.time() * 1000))
        msg2 = ts2 + 'POST' + '/api/v2/mix/order/place-tpsl-order' + body_str
        sig2 = base64.b64encode(hmac.new(secret_key.encode('utf-8'), msg2.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
        headers2 = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sig2,
            'ACCESS-TIMESTAMP': ts2,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
        async with session.post('https://api.bitget.com/api/v2/mix/order/place-tpsl-order', data=body_str, headers=headers2) as resp2:
            res = await resp2.json()
            print('SL SET RESULT:', json.dumps(res, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
