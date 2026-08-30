import json, os, hmac, hashlib, base64, time, requests

def check_short_plan_orders():
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
    
    # 1. Check live position
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
    
    if btc_pos:
        print(f"Active Position: {btc_pos.get('holdSide')} {btc_pos.get('total')} BTC @ ${btc_pos.get('openPriceAvg')}")
    else:
        print("No active position!")
        return

    # 2. Cancel all old plan orders for BTCUSDT
    old_ids = ["1475733867349401601", "1475733867867922432"]
    for oid in old_ids:
        path_cancel = "/api/v2/mix/order/cancel-plan-order"
        body = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "orderId": oid})
        ts = str(int(time.time() * 1000))
        msg = ts + "POST" + path_cancel + body
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
        res_c = requests.post(url_base + path_cancel, headers=headers, data=body, timeout=5)
        print(f"Cancel Old Order {oid}: {res_c.json()}")

    # 3. Place Two 50% Stop-Loss Orders for Short
    total_qty = float(btc_pos.get("total", 0.1146))
    half_1 = round(total_qty / 2.0, 4)
    half_2 = round(total_qty - half_1, 4)
    
    # 1차 50%: $77,850.0 (전고점 77,825 뚫릴 시 1차 50% 칼손절 방어)
    # 2차 50%: $78,050.0 (78K 돌파 시 잔여 50% 최종 컷)
    sl1_price = "77850.0"
    sl2_price = "78050.0"
    
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": sl1_price,
        "triggerType": "mark_price",
        "size": str(half_1),
        "holdSide": "short"
    }
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": sl2_price,
        "triggerType": "mark_price",
        "size": str(half_2),
        "holdSide": "short"
    }
    
    for name, b_dict in [(f"1st 50% SL @ ${sl1_price} (Size {half_1})", sl1_body), (f"2nd 50% SL @ ${sl2_price} (Size {half_2})", sl2_body)]:
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
        print(f"[{name}] Result: {res_o.status_code} {res_o.json()}")

check_short_plan_orders()