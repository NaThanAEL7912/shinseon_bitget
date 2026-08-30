import json, os, hmac, hashlib, base64, time, requests

def test_partial_sl():
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
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    
    # 50% Stop Loss at $76,490.0 (King's key pivot floor)
    sl_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "76490.0",
        "triggerType": "mark_price",
        "size": "0.0685",
        "holdSide": "long"
    }
    
    b_json = json.dumps(sl_body)
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
    print("Partial 50% SL Order Result:", res.status_code, res.json())

test_partial_sl()