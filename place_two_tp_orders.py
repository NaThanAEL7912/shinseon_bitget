import json, os, hmac, hashlib, base64, time, requests

def place_two_tps():
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
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    
    # 1. First 50% TP: $77,950.0 / Size 0.019 BTC
    tp1_price = "77950.0"
    tp1_size = "0.019"
    tp1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": tp1_price,
        "triggerType": "mark_price",
        "size": tp1_size,
        "holdSide": "long"
    }
    
    # 2. Second 50% TP: $78,450.0 / Size 0.020 BTC
    tp2_price = "78450.0"
    tp2_size = "0.020"
    tp2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": tp2_price,
        "triggerType": "mark_price",
        "size": tp2_size,
        "holdSide": "long"
    }
    
    for name, b_dict in [("1st TP (50%) @ $77,950", tp1_body), ("2nd TP (50%) @ $78,450", tp2_body)]:
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
        print(f"[{name}] Result -> {res.status_code}: {res.json()}")

place_two_tps()