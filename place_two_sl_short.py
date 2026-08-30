import json, os, hmac, hashlib, base64, time, requests

def place_two_sl_short():
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
    
    entry_p = 77702.1
    total_qty = 0.1146
    half_qty_1 = 0.0573
    half_qty_2 = 0.0573
    
    # 1. 1st 50% SL @ +0.45% ($78,050.0 - 78K 돌파 시 1차 50% 방어)
    # 2. 2nd 50% SL @ +0.70% ($78,250.0 - 최종 50% 컷)
    sl1_price = "78050.0"
    sl2_price = "78250.0"
    
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": sl1_price,
        "triggerType": "mark_price",
        "size": str(half_qty_1),
        "holdSide": "short"
    }
    
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": sl2_price,
        "triggerType": "mark_price",
        "size": str(half_qty_2),
        "holdSide": "short"
    }
    
    for name, b_dict in [("1st 50% SL (Short @ $78,050)", sl1_body), ("2nd 50% SL (Short @ $78,250)", sl2_body)]:
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
        print(f"[{name}] Result: {res.status_code} {res.json()}")

place_two_sl_short()