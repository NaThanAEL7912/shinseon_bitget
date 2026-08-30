import json, os, hmac, hashlib, base64, time, requests

def place_king_tps():
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
    
    # 1. Get Live Position
    path_pos = "/api/v2/mix/position/all-position?productType=USDT-FUTURES"
    t_pos = str(int(time.time() * 1000))
    msg_pos = t_pos + "GET" + "/api/v2/mix/position/all-position" + "?" + "productType=USDT-FUTURES"
    mac_p = hmac.new(secret_key.encode('utf-8'), msg_pos.encode('utf-8'), hashlib.sha256)
    sign_p = base64.b64encode(mac_p.digest()).decode('utf-8')
    headers_p = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign_p,
        'ACCESS-TIMESTAMP': t_pos,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }
    r = requests.get(url_base + "/api/v2/mix/position/all-position?productType=USDT-FUTURES", headers=headers_p, timeout=5)
    data = r.json().get("data", [])
    btc_pos = next((p for p in data if p.get("symbol") == "BTCUSDT" and float(p.get("total", 0)) > 0), None)
    
    if not btc_pos:
        print("No active BTC position found!")
        return
        
    total_qty = float(btc_pos.get("total", 0))
    entry_p = float(btc_pos.get("openPriceAvg", 0))
    side = btc_pos.get("holdSide")
    lev = btc_pos.get("leverage")
    
    print(f"Active Position: {side.upper()} {total_qty} BTC @ ${entry_p:,.2f} ({lev}x)")
    
    half_1 = round(total_qty / 2.0, 4)
    half_2 = round(total_qty - half_1, 4)
    
    # King's Requested TP: 78500 and 78000 for SHORT
    tp1_p = "78500.0"
    tp2_p = "78000.0"
    
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    tp1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": tp1_p,
        "triggerType": "mark_price",
        "size": str(half_1),
        "holdSide": side.lower()
    }
    tp2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": tp2_p,
        "triggerType": "mark_price",
        "size": str(half_2),
        "holdSide": side.lower()
    }
    
    # Optional protective SL at 79750
    sl_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "79750.0",
        "triggerType": "mark_price",
        "size": str(total_qty),
        "holdSide": side.lower()
    }
    
    orders = [
        (f"1st 50% TP @ ${tp1_p} (Qty {half_1})", tp1_body),
        (f"2nd 50% TP @ ${tp2_p} (Qty {half_2})", tp2_body),
        (f"Emergency SL @ $79750.0 (Qty {total_qty})", sl_body)
    ]
    
    for name, b_dict in orders:
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

place_king_tps()