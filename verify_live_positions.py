import json, os, hmac, hashlib, base64, time, requests

def check_pos():
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
    path_pos = "/api/v2/mix/position/all-position"
    params_pos = "productType=USDT-FUTURES"
    timestamp = str(int(time.time() * 1000))
    message = timestamp + "GET" + path_pos + "?" + params_pos
    mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }
    resp = requests.get(f"{url_base}{path_pos}?{params_pos}", headers=headers, timeout=5)
    r_json = resp.json()
    pos_list = r_json.get("data", []) or []
    print("=== LIVE BITGET POSITIONS ===")
    active_count = 0
    for p in pos_list:
        total = float(p.get("total", 0.0) or 0.0)
        if total > 0:
            active_count += 1
            print(f"- Symbol: {p.get('symbol')} | Side: {p.get('holdSide')} | Total: {total} | Entry: ${p.get('openPriceAvg')} | PnL: ${p.get('unrealizedPL')}")
    if active_count == 0:
        print("- NO ACTIVE POSITIONS")

check_pos()