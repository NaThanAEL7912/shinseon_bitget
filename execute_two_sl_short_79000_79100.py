import json, os, hmac, hashlib, base64, time, requests

def execute_two_sl_short():
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
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    
    # 1차 손절: 1.2284 BTC @ $79,000.0 (SHORT)
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "79000.0",
        "triggerType": "mark_price",
        "size": "1.2284",
        "holdSide": "short"
    }
    
    # 2차 손절: 1.2285 BTC @ $79,100.0 (SHORT)
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "79100.0",
        "triggerType": "mark_price",
        "size": "1.2285",
        "holdSide": "short"
    }
    
    results = []
    for name, b_dict in [("1차 50% 숏 손절 방패 ($79,000.0 / 1.2284 BTC)", sl1_body), ("2차 50% 숏 손절 방패 ($79,100.0 / 1.2285 BTC)", sl2_body)]:
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
    execute_two_sl_short()
