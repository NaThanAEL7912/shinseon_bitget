import json, os, hmac, hashlib, base64, time, requests

def fix_50pct_stop():
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
    
    # 1. Check exact live BTC position
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
    
    if not btc_pos:
        print("No active BTC position found!")
        return
        
    total_qty = float(btc_pos.get("total", 0.0))
    entry_price = float(btc_pos.get("openPriceAvg", 0.0))
    print(f"Exact Live BTC Position: {total_qty} BTC @ ${entry_price:,.2f}")
    
    # Calculate exact 50%
    half_qty = round(total_qty * 0.5, 4)
    print(f"Exact 50% Size to Protect: {half_qty} BTC (out of {total_qty} BTC)")
    
    # 2. Place New Protective Stop at $77,250.0
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    new_sl_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "77250.0",
        "triggerType": "mark_price",
        "size": str(half_qty),
        "holdSide": "long"
    }
    
    b_json = json.dumps(new_sl_body)
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
    print("New 50% Protective Stop @ $77,250 Result:", res.status_code, res.json())

fix_50pct_stop()