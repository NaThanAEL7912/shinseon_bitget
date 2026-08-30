import json, os, hmac, hashlib, base64, time, requests

def cancel_specific_old_orders():
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
    path_cancel = "/api/v2/mix/order/cancel-plan-order"
    
    # Old order IDs
    old_ids = ["1475702366763184128", "1475702367172681728"]
    for oid in old_ids:
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
        res = requests.post(url_base + path_cancel, headers=headers, data=body, timeout=5)
        print(f"Cancel Old Order {oid}: {res.json()}")

cancel_specific_old_orders()