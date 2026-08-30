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
        # 1. 포지션 실시간 조회
        async with session.get('https://api.bitget.com' + path_pos + '?' + params, headers=headers) as resp:
            data = await resp.json()
            pos_list = data.get('data', [])
            total_qty = 1.239
            for p in pos_list:
                if p.get('holdSide') == 'long' and float(p.get('total', 0)) > 0:
                    total_qty = float(p.get('total'))
        
        qty_1 = round(total_qty * 0.5, 4)
        qty_2 = round(total_qty - qty_1, 4)
        print(f"Total Position: {total_qty} BTC -> TP1: {qty_1} BTC @ 69450, TP2: {qty_2} BTC @ 70500, SL: {total_qty} BTC @ 68100")

        # 2. 기존 미체결 플랜/TP/SL 주문 취소 (Clean up old TPSL)
        path_cancel = '/api/v2/mix/order/cancel-all-orders'
        cancel_body = {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT'
        }
        # 또는 cancel-plan-order 사용

        # 3. 1차 익절 발주 (69,450 / qty_1)
        tp1_body = {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'pos_profit',
            'triggerPrice': '69450.0',
            'triggerType': 'mark_price',
            'size': str(qty_1),
            'holdSide': 'long'
        }
        body_str1 = json.dumps(tp1_body)
        ts1 = str(int(time.time() * 1000))
        msg1 = ts1 + 'POST' + '/api/v2/mix/order/place-tpsl-order' + body_str1
        sig1 = base64.b64encode(hmac.new(secret_key.encode('utf-8'), msg1.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
        headers1 = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sig1,
            'ACCESS-TIMESTAMP': ts1,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
        async with session.post('https://api.bitget.com/api/v2/mix/order/place-tpsl-order', data=body_str1, headers=headers1) as r1:
            res1 = await r1.json()
            print('TP1 RESULT (69450.0):', res1)

        # 4. 2차 익절 발주 (70,500 / qty_2)
        tp2_body = {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'pos_profit',
            'triggerPrice': '70500.0',
            'triggerType': 'mark_price',
            'size': str(qty_2),
            'holdSide': 'long'
        }
        body_str2 = json.dumps(tp2_body)
        ts2 = str(int(time.time() * 1000))
        msg2 = ts2 + 'POST' + '/api/v2/mix/order/place-tpsl-order' + body_str2
        sig2 = base64.b64encode(hmac.new(secret_key.encode('utf-8'), msg2.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
        headers2 = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sig2,
            'ACCESS-TIMESTAMP': ts2,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
        async with session.post('https://api.bitget.com/api/v2/mix/order/place-tpsl-order', data=body_str2, headers=headers2) as r2:
            res2 = await r2.json()
            print('TP2 RESULT (70500.0):', res2)

        # 5. 스탑로스 발주 (68,100 / total_qty)
        sl_body = {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'pos_loss',
            'triggerPrice': '68100.0',
            'triggerType': 'mark_price',
            'size': str(total_qty),
            'holdSide': 'long'
        }
        body_str3 = json.dumps(sl_body)
        ts3 = str(int(time.time() * 1000))
        msg3 = ts3 + 'POST' + '/api/v2/mix/order/place-tpsl-order' + body_str3
        sig3 = base64.b64encode(hmac.new(secret_key.encode('utf-8'), msg3.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
        headers3 = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sig3,
            'ACCESS-TIMESTAMP': ts3,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
        async with session.post('https://api.bitget.com/api/v2/mix/order/place-tpsl-order', data=body_str3, headers=headers3) as r3:
            res3 = await r3.json()
            print('SL RESULT (68100.0):', res3)

if __name__ == '__main__':
    asyncio.run(main())
