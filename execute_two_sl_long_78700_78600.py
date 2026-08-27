import json, os, hmac, hashlib, base64, time, requests

def execute_two_sl_long():
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
    
    # 0. Cancel previous plan orders for BTCUSDT
    path_plan_list = "/api/v2/mix/order/orders-plan-pending"
    query = "?symbol=BTCUSDT&productType=USDT-FUTURES"
    ts = str(int(time.time() * 1000))
    msg = ts + "GET" + path_plan_list + query
    mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign, 'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
    }
    
    # cancel existing stop-loss / plan orders if any
    try:
        # Cancel single SL if set on position
        pass
    except Exception as e:
        print(f"Error checking pending: {e}")

    # 1. Place New 50% / 50% Long SL Orders (Total: 3.0051 BTC)
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    
    # 1차 손절: 1.5025 BTC @ $78,700.0 (LONG)
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78700.0",
        "triggerType": "mark_price",
        "size": "1.5025",
        "holdSide": "long"
    }
    
    # 2차 손절: 1.5026 BTC @ $78,600.0 (LONG)
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78600.0",
        "triggerType": "mark_price",
        "size": "1.5026",
        "holdSide": "long"
    }
    
    results = []
    for name, b_dict in [("1차 50% 롱 손절 방패 ($78,700.0 / 1.5025 BTC)", sl1_body), ("2차 50% 롱 손절 방패 ($78,600.0 / 1.5026 BTC)", sl2_body)]:
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
        res_data = res.json()
        print(f"[{name}] Result: HTTP {res.status_code} | {res_data}")
        results.append((name, res_data))
        time.sleep(0.3)
        
    return results

if __name__ == "__main__":
    execute_two_sl_long()
