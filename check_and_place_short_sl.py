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
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        cfg[k.strip()] = v.strip().strip('"').strip("'")
        except Exception as e:
            print(f"Error reading .env: {e}")

    if not (cfg.get("BITGET_API_KEY") and cfg.get("BITGET_SECRET_KEY") and cfg.get("BITGET_PASSPHRASE")):
        for sc_path in ["server_config.json", "/home/ubuntu/server_config.json", "c:\\Working\\ShinSeon_Bitget\\server_config.json"]:
            if os.path.exists(sc_path):
                try:
                    with open(sc_path, "r", encoding="utf-8") as f:
                        sc = json.load(f)
                        for k in ["BITGET_API_KEY", "BITGET_SECRET_KEY", "BITGET_PASSPHRASE"]:
                            if sc.get(k):
                                cfg[k] = sc[k]
                except Exception as e:
                    print(f"Error reading {sc_path}: {e}")

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
    print(f"API Key: {api_key[:4]}****{api_key[-4:] if api_key else ''}")
    
    # 1. Check position
    path_pos = "/api/v2/mix/position/all-position?productType=USDT-FUTURES"
    pos_res = make_request("GET", path_pos, api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print("ALL POSITIONS RES:")
    print(json.dumps(pos_res, indent=2, ensure_ascii=False))

    # Market ticker
    t_res = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
    print("MARKET TICKER:")
    print(json.dumps(t_res, indent=2, ensure_ascii=False))

    # Pending plan orders
    path_pending = "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES"
    pending_res = make_request("GET", path_pending, api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    print("PENDING ORDERS:")
    print(json.dumps(pending_res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
