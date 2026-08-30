import json, os, hmac, hashlib, base64, time, requests

def check_plan():
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
    path_list = "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES"
    ts = str(int(time.time() * 1000))
    msg = ts + "GET" + "/api/v2/mix/order/orders-plan-pending" + "?" + "symbol=BTCUSDT&productType=USDT-FUTURES"
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
    r = requests.get(url_base + "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES", headers=headers, timeout=5)
    print("Pending Orders Response:", r.json())

check_plan()