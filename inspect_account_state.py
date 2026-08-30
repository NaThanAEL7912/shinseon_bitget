import os
import sys
import json
import time
import hmac
import hashlib
import base64
import requests

def load_credentials():
    cfg = {}
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg.get("BITGET_API_KEY"), cfg.get("BITGET_SECRET_KEY"), cfg.get("BITGET_PASSPHRASE")

def make_request(method, path, body_dict=None, api_key=None, secret_key=None, passphrase=None):
    url_base = "https://api.bitget.com"
    body_str = json.dumps(body_dict) if body_dict is not None else ""
    ts = str(int(time.time() * 1000))
    msg = ts + method.upper() + path + body_str
    mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
        'locale': 'ko-KR'
    }
    url = url_base + path
    if method.upper() == "GET":
        resp = requests.get(url, headers=headers, timeout=10)
    elif method.upper() == "POST":
        resp = requests.post(url, headers=headers, data=body_str, timeout=10)
    else:
        raise ValueError(f"Unsupported method: {method}")
    return resp.json()

def main():
    api_key, secret_key, passphrase = load_credentials()
    
    print("=== 1. ALL POSITIONS ===")
    p1 = make_request("GET", "/api/v2/mix/position/all-position?productType=USDT-FUTURES", api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print(json.dumps(p1, indent=2, ensure_ascii=False))

    print("\n=== 2. SINGLE POSITION (BTCUSDT) ===")
    p2 = make_request("GET", "/api/v2/mix/position/single-position?symbol=BTCUSDT&productType=USDT-FUTURES&marginCoin=USDT", api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print(json.dumps(p2, indent=2, ensure_ascii=False))

    print("\n=== 3. ACCOUNT BALANCE ===")
    b1 = make_request("GET", "/api/v2/mix/account/accounts?productType=USDT-FUTURES", api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print(json.dumps(b1, indent=2, ensure_ascii=False))

    print("\n=== 4. RECENT FILLS (BTCUSDT) ===")
    f1 = make_request("GET", "/api/v2/mix/order/fills?symbol=BTCUSDT&productType=USDT-FUTURES&limit=10", api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print(json.dumps(f1, indent=2, ensure_ascii=False))

    print("\n=== 5. PENDING PLAN ORDERS (profit_loss) ===")
    pl1 = make_request("GET", "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss", api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print(json.dumps(pl1, indent=2, ensure_ascii=False))

    print("\n=== 6. PENDING PLAN ORDERS (loss_plan) ===")
    pl2 = make_request("GET", "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=loss_plan", api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print(json.dumps(pl2, indent=2, ensure_ascii=False))

    print("\n=== 7. PENDING REGULAR ORDERS ===")
    po = make_request("GET", "/api/v2/mix/order/orders-pending?symbol=BTCUSDT&productType=USDT-FUTURES", api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print(json.dumps(po, indent=2, ensure_ascii=False))

    print("\n=== 8. MARKET TICKER ===")
    t_res = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
    print(json.dumps(t_res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
