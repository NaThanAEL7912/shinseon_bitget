import json, os, hmac, hashlib, base64, time, requests

def check_final_wrap():
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
    
    # Check position
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
    active = [p for p in pos_data if float(p.get("total", 0)) > 0]
    print(f"Active Positions Count: {len(active)}")
    
    # Check account balance
    path_acc = "/api/v2/mix/account/accounts"
    params_acc = "productType=USDT-FUTURES"
    t_acc = str(int(time.time() * 1000))
    msg_acc = t_acc + "GET" + path_acc + "?" + params_acc
    mac_a = hmac.new(secret_key.encode('utf-8'), msg_acc.encode('utf-8'), hashlib.sha256)
    sign_a = base64.b64encode(mac_a.digest()).decode('utf-8')
    headers_a = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign_a,
        'ACCESS-TIMESTAMP': t_acc,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }
    r_acc = requests.get(f"{url_base}{path_acc}?{params_acc}", headers=headers_a, timeout=5)
    acc_list = r_acc.json().get("data", [])
    usdt_acc = next((a for a in acc_list if a.get("marginCoin") == "USDT"), {})
    equity = float(usdt_acc.get("usdtEquity", 0.0) or usdt_acc.get("equity", 0.0) or 0.0)
    print(f"Final USDT Account Equity: ${equity:,.2f} USDT")

check_final_wrap()