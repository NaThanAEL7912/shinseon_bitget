import json, os, hmac, hashlib, base64, time, requests

def place_stop_at_77250():
    cfg = {}
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
                
    api_key = cfg.get("BITGET_API_KEY")
    secret_key = cfg.get("BITGET_SECRET_KEY")
    passphrase = cfg.get("BITGET_PASSPHRASE")
    
    url_base = "https://api.bitget.com"
    
    # 1. Cancel previous $76,490 SL order if exists
    path_cancel = "/api/v2/mix/order/cancel-plan-order"
    old_sl_id = "1475715175746625536"
    body_cancel = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "orderId": old_sl_id})
    ts = str(int(time.time() * 1000))
    msg = ts + "POST" + path_cancel + body_cancel
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
    r_c = requests.post(url_base + path_cancel, headers=headers, data=body_cancel, timeout=5)
    print("Cancel Old $76,490 SL:", r_c.json())
    
    # 2. Place New Protective Stop at $77,250.0 (Size: 0.0685 BTC / 50%)
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    new_sl_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "77250.0",
        "triggerType": "mark_price",
        "size": "0.0685",
        "holdSide": "long"
    }
    
    b_json = json.dumps(new_sl_body)
    ts2 = str(int(time.time() * 1000))
    msg2 = ts2 + "POST" + path_plan + b_json
    mac2 = hmac.new(secret_key.encode('utf-8'), msg2.encode('utf-8'), hashlib.sha256)
    sign2 = base64.b64encode(mac2.digest()).decode('utf-8')
    headers2 = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign2,
        'ACCESS-TIMESTAMP': ts2,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }
    r_new = requests.post(url_base + path_plan, headers=headers2, data=b_json, timeout=5)
    print("New Protective Stop @ $77,250 Result:", r_new.status_code, r_new.json())

place_stop_at_77250()