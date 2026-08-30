import json, os, hmac, hashlib, base64, time, requests

def ensure_safe_sl_for_shinseon_long():
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
    
    total_qty = 0.7321
    half_1 = "0.3660"
    half_2 = "0.3661"
    
    # 1. Cancel old plan orders that might be outdated with smaller sizes
    # Place 2 fresh SL orders above liquidation ($78,460)
    # SL 1: $78,620.0 (1차 50%)
    # SL 2: $78,520.0 (2차 50%)
    
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78620.0",
        "triggerType": "mark_price",
        "size": half_1,
        "holdSide": "long"
    }
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78520.0",
        "triggerType": "mark_price",
        "size": half_2,
        "holdSide": "long"
    }
    
    # Also 50% TP at 79800 and 82000
    tp1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": "79800.0",
        "triggerType": "mark_price",
        "size": half_1,
        "holdSide": "long"
    }
    tp2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": "82000.0",
        "triggerType": "mark_price",
        "size": half_2,
        "holdSide": "long"
    }
    
    for name, b_dict in [("1st 50% SL @ $78,620", sl1_body), ("2nd 50% SL @ $78,520", sl2_body), ("1st 50% TP @ $79,800", tp1_body), ("2nd 50% TP @ $82,000", tp2_body)]:
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

ensure_safe_sl_for_shinseon_long()