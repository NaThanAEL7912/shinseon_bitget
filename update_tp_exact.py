import json, os, hmac, hashlib, base64, time, requests

def update_tp_orders_exact():
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
    
    # 1. Cancel all previous plan orders for BTCUSDT
    path_cancel_plan = "/api/v2/mix/order/cancel-all-plan-orders"
    body_cancel = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES"})
    ts = str(int(time.time() * 1000))
    msg = ts + "POST" + path_cancel_plan + body_cancel
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
    r_cancel = requests.post(url_base + path_cancel_plan, headers=headers, data=body_cancel, timeout=5)
    print("Cancel Old Plan Orders:", r_cancel.json())
    
    # 2. Check live position size
    path_pos = "/api/v2/mix/position/all-position"
    params_pos = "productType=USDT-FUTURES"
    t_pos = str(int(time.time() * 1000))
    msg_pos = t_pos + "GET" + path_pos + "?" + params_pos
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
    r_pos = requests.get(f"{url_base}{path_pos}?{params_pos}", headers=headers_p, timeout=5)
    pos_data = r_pos.json().get("data", [])
    btc_pos = next((p for p in pos_data if p.get("symbol") == "BTCUSDT" and float(p.get("total", 0)) > 0), None)
    
    total_qty = float(btc_pos.get("total", 0.1371)) if btc_pos else 0.1371
    entry_price = float(btc_pos.get("openPriceAvg", 76910.0)) if btc_pos else 76910.0
    print(f"Verified Live BTC Position: {total_qty} BTC @ ${entry_price:,.1f}")
    
    # 3. Calculate 50% split for 0.1371 BTC
    half_1 = round(total_qty / 2.0, 4)       # 0.0685
    half_2 = round(total_qty - half_1, 4)     # 0.0686
    print(f"Splitting into -> 1st TP: {half_1} BTC, 2nd TP: {half_2} BTC (Sum: {half_1 + half_2} BTC)")
    
    # 4. Place 1st TP @ $77,950
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    tp1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": "77950.0",
        "triggerType": "mark_price",
        "size": str(half_1),
        "holdSide": "long"
    }
    
    # 5. Place 2nd TP @ $78,450
    tp2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "profit_plan",
        "triggerPrice": "78450.0",
        "triggerType": "mark_price",
        "size": str(half_2),
        "holdSide": "long"
    }
    
    for name, b_dict in [("1st TP (50%) @ $77,950", tp1_body), ("2nd TP (50%) @ $78,450", tp2_body)]:
        b_json = json.dumps(b_dict)
        ts_order = str(int(time.time() * 1000))
        msg_o = ts_order + "POST" + path_plan + b_json
        mac_o = hmac.new(secret_key.encode('utf-8'), msg_o.encode('utf-8'), hashlib.sha256)
        sign_o = base64.b64encode(mac_o.digest()).decode('utf-8')
        headers_o = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sign_o,
            'ACCESS-TIMESTAMP': ts_order,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
        res_o = requests.post(url_base + path_plan, headers=headers_o, data=b_json, timeout=5)
        print(f"[{name} -> Size: {b_dict['size']} BTC] Result -> {res_o.status_code}: {res_o.json()}")

update_tp_orders_exact()