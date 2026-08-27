import json, os, hmac, hashlib, base64, time, requests

def execute_two_sl_short():
    cfg = {}
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
                    
    api_key = cfg.get("BITGET_API_KEY")
    secret_key = cfg.get("BITGET_SECRET_KEY")
    passphrase = cfg.get("BITGET_PASSPHRASE")
    
    url_base = "https://api.bitget.com"
    
    # 0. Cancel previous plan orders
    path_pending = "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES"
    ts = str(int(time.time() * 1000))
    msg = ts + "GET" + "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES"
    mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign, 'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
    }
    r = requests.get(url_base + "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES", headers=headers)
    pending_list = (r.json().get("data") or {}).get("entrustedList", []) or []
    print(f"Cancelling {len(pending_list)} old plan orders...")
    for o in pending_list:
        oid = o.get("orderId")
        path_cancel = "/api/v2/mix/order/cancel-plan-order"
        body = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "orderId": oid})
        ts_c = str(int(time.time() * 1000))
        msg_c = ts_c + "POST" + path_cancel + body
        mac_c = hmac.new(secret_key.encode('utf-8'), msg_c.encode('utf-8'), hashlib.sha256)
        sign_c = base64.b64encode(mac_c.digest()).decode('utf-8')
        headers_c = {
            'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign_c, 'ACCESS-TIMESTAMP': ts_c,
            'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
        }
        res_c = requests.post(url_base + path_cancel, headers=headers_c, data=body)
        print(f"Cancel {oid}: {res_c.json()}")
    
    time.sleep(0.5)

    # 1. Place New 50% / 50% Short SL Orders (Total: 4.1078 BTC)
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    
    # 1차 손절: 2.0539 BTC @ $78,800.0 (SHORT)
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78800.0",
        "triggerType": "mark_price",
        "size": "2.0539",
        "holdSide": "short"
    }
    
    # 2차 손절: 2.0539 BTC @ $78,900.0 (SHORT)
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78900.0",
        "triggerType": "mark_price",
        "size": "2.0539",
        "holdSide": "short"
    }
    
    results = []
    for name, b_dict in [("1차 50% 숏 손절 방패 ($78,800.0 / 2.0539 BTC)", sl1_body), ("2차 50% 숏 손절 방패 ($78,900.0 / 2.0539 BTC)", sl2_body)]:
        b_json = json.dumps(b_dict)
        ts = str(int(time.time() * 1000))
        msg = ts + "POST" + path_plan + b_json
        mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
        sign = base64.b64encode(mac.digest()).decode('utf-8')
        headers = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sign,
            'ACCESS-TIMESTAMP': ts,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
        res = requests.post(url_base + path_plan, headers=headers, data=b_json, timeout=5)
        res_data = res.json()
        print(f"[{name}] Result: HTTP {res.status_code} | {res_data}")
        results.append((name, res_data))
        time.sleep(0.3)
        
    return results

if __name__ == "__main__":
    execute_two_sl_short()
