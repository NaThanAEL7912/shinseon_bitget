import json, os, hmac, hashlib, base64, time, requests

def update_two_50pct_sl():
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
    
    print(f"Active Position: {side} {total_qty} BTC @ ${entry_p:,.2f} ({lev}x)")
    
    # Get Current Price
    r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
    mark_p = float(r_t['data'][0].get('markPrice', 0))
    print(f"Current Mark Price: ${mark_p:,.2f}")
    
    # 2. Cancel all existing plan orders for BTCUSDT
    path_cancel_all = "/api/v2/mix/order/cancel-symbol-plan-orders"
    body_ca = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES"})
    ts_ca = str(int(time.time() * 1000))
    msg_ca = ts_ca + "POST" + path_cancel_all + body_ca
    mac_ca = hmac.new(secret_key.encode('utf-8'), msg_ca.encode('utf-8'), hashlib.sha256)
    sign_ca = base64.b64encode(mac_ca.digest()).decode('utf-8')
    headers_ca = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign_ca,
        'ACCESS-TIMESTAMP': ts_ca,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }
    r_ca = requests.post(url_base + path_cancel_all, headers=headers_ca, data=body_ca, timeout=5)
    print(f"Cancel All Old Plans Result: {r_ca.json()}")

    # 3. Calculate 50% splits
    half_1 = round(total_qty / 2.0, 4)
    half_2 = round(total_qty - half_1, 4)
    
    # Calculate SL Prices based on Side
    if side.lower() == "long":
        # For Long: SL must be < current mark price
        # 1차 50%: mark_p - 150 (tight safety guard)
        # 2차 50%: mark_p - 350 (structural support)
        # If entry is below, set above or at entry
        sl1_p = str(round(min(mark_p - 120.0, max(entry_p + 50.0, mark_p - 120.0)), 1))
        if float(sl1_p) >= mark_p:
            sl1_p = str(round(mark_p - 100.0, 1))
            
        sl2_p = str(round(float(sl1_p) - 200.0, 1))
        if float(sl2_p) >= float(sl1_p):
            sl2_p = str(round(float(sl1_p) - 150.0, 1))
            
    else: # short
        sl1_p = str(round(mark_p + 120.0, 1))
        sl2_p = str(round(mark_p + 320.0, 1))
        
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": sl1_p,
        "triggerType": "mark_price",
        "size": str(half_1),
        "holdSide": side.lower()
    }
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": sl2_p,
        "triggerType": "mark_price",
        "size": str(half_2),
        "holdSide": side.lower()
    }
    
    for name, b_dict in [(f"1st 50% SL @ ${sl1_p} (Qty {half_1})", sl1_body), (f"2nd 50% SL @ ${sl2_p} (Qty {half_2})", sl2_body)]:
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

update_two_50pct_sl()