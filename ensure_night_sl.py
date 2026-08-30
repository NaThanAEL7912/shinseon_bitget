import json, os, hmac, hashlib, base64, time, requests

def check_and_ensure_sl():
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
    
    # 1. Place 2x 50% Stop-Loss orders for the full 0.4357 BTC position
    # Total Qty: 0.4357 BTC
    # 1st 50% SL: 0.2178 BTC @ $78,350.0 (전고점 넥라인 아래)
    # 2nd 50% SL: 0.2179 BTC @ $78,050.0 (78K 라운드피겨 아래)
    
    half_1 = "0.2178"
    half_2 = "0.2179"
    
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78350.0",
        "triggerType": "mark_price",
        "size": half_1,
        "holdSide": "long"
    }
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78050.0",
        "triggerType": "mark_price",
        "size": half_2,
        "holdSide": "long"
    }
    
    for name, b_dict in [("1st 50% SL @ $78,350", sl1_body), ("2nd 50% SL @ $78,050", sl2_body)]:
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

check_and_ensure_sl()