import json, os, hmac, hashlib, base64, time, requests

def place_morning_short_tps():
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
    
    total_qty = 0.8233
    half_1 = "0.4116"
    half_2 = "0.4117"
    
    # TP 1: $80,100.0 (80K 라운드피겨 넥라인)
    # TP 2: $79,500.0 (1시간봉 MA7 지지대)
    # SL: $80,950.0 (비상 안전 방패)
    
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    tp1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": "80100.0",
        "triggerType": "mark_price",
        "size": half_1,
        "holdSide": "short"
    }
    tp2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": "79500.0",
        "triggerType": "mark_price",
        "size": half_2,
        "holdSide": "short"
    }
    sl_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "80950.0",
        "triggerType": "mark_price",
        "size": str(total_qty),
        "holdSide": "short"
    }
    
    for name, b_dict in [("1st 50% TP @ $80,100", tp1_body), ("2nd 50% TP @ $79,500", tp2_body), ("Emergency SL @ $80,950", sl_body)]:
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

place_morning_short_tps()