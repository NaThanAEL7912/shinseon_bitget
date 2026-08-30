import os, sys, json, time, hmac, hashlib, base64, requests

def main():
    api_key = 'bg_670c7963afe129099346583180ce606b'
    secret_key = '4fe82e41304e84e315c7aa222ead7a4307182ec5f4766c37ad2290bf4268a2a0'
    passphrase = 'shinsun1234567'
    url_base = 'https://api.bitget.com'

    # 1. 1st 50% SL @ ,650.0 (1.3486 BTC)
    # 2. 2nd 50% SL @ ,450.0 (1.3487 BTC)
    orders = [
        ('1st 50% SL (Long @ ,650.0)', {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'loss_plan',
            'triggerPrice': '77650.0',
            'triggerType': 'mark_price',
            'size': '1.3486',
            'holdSide': 'long'
        }),
        ('2nd 50% SL (Long @ ,450.0)', {
            'symbol': 'BTCUSDT',
            'productType': 'USDT-FUTURES',
            'marginCoin': 'USDT',
            'planType': 'loss_plan',
            'triggerPrice': '77450.0',
            'triggerType': 'mark_price',
            'size': '1.3487',
            'holdSide': 'long'
        })
    ]

    path_plan = '/api/v2/mix/order/place-tpsl-order'
    results = []
    for name, b_dict in orders:
        b_json = json.dumps(b_dict)
        ts = str(int(time.time() * 1000))
        msg = ts + 'POST' + path_plan + b_json
        mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
        sign = base64.b64encode(mac.digest()).decode('utf-8')
        headers = {
            'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign, 'ACCESS-TIMESTAMP': ts,
            'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'ko-KR'
        }
        res = requests.post(url_base + path_plan, headers=headers, data=b_json, timeout=10).json()
        print(f'[{name}] Result:', res)
        results.append(res)
        time.sleep(0.3)

    # Verify
    path_check = '/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss'
    ts_c = str(int(time.time() * 1000))
    msg_c = ts_c + 'GET' + path_check
    mac_c = hmac.new(secret_key.encode('utf-8'), msg_c.encode('utf-8'), hashlib.sha256)
    sign_c = base64.b64encode(mac_c.digest()).decode('utf-8')
    headers_c = {
        'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign_c, 'ACCESS-TIMESTAMP': ts_c,
        'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'ko-KR'
    }
    pending = requests.get(url_base + path_check, headers=headers_c, timeout=10).json()
    print('\n=== PENDING PLAN ORDERS ===\n', json.dumps(pending, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
