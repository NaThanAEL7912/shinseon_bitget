import json, os, hmac, hashlib, base64, time, requests

def clean_and_verify_plan_orders():
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
    path_list = "/api/v2/mix/order/orders-plan-pending"
    params = "symbol=BTCUSDT&productType=USDT-FUTURES"
    
    ts = str(int(time.time() * 1000))
    msg = ts + "GET" + path_list + "?" + params
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
    r = requests.get(f"{url_base}{path_list}?{params}", headers=headers, timeout=5)
    orders = r.json().get("data", {}).get("entrustedList", []) or []
    print("=== CURRENT ACTIVE BTC PLAN ORDERS ON BITGET ===")
    for o in orders:
        oid = o.get("orderId")
        size = o.get("size")
        tp_price = o.get("triggerPrice")
        print(f"• Order ID: {oid} | Trigger: ${tp_price} | Size: {size} BTC | PlanType: {o.get('planType')}")
        # If size is old 0.019 or 0.020, cancel it
        if size in ["0.019", "0.02"]:
            path_cancel = "/api/v2/mix/order/cancel-plan-order"
            body = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "orderId": oid})
            t_c = str(int(time.time() * 1000))
            m_c = t_c + "POST" + path_cancel + body
            mac_c = hmac.new(secret_key.encode('utf-8'), m_c.encode('utf-8'), hashlib.sha256)
            sign_c = base64.b64encode(mac_c.digest()).decode('utf-8')
            headers_c = {
                'ACCESS-KEY': api_key,
                'ACCESS-SIGN': sign_c,
                'ACCESS-TIMESTAMP': t_c,
                'ACCESS-PASSPHRASE': passphrase,
                'Content-Type': 'application/json',
                'locale': 'en-US'
            }
            res_c = requests.post(url_base + path_cancel, headers=headers_c, data=body, timeout=5)
            print(f"  -> Cancelled Old Order {oid}: {res_c.json()}")

clean_and_verify_plan_orders()