import json, os, hmac, hashlib, base64, time, requests

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
path_act = "/api/v2/mix/account/accounts?productType=USDT-FUTURES"
t_act = str(int(time.time() * 1000))
msg_act = t_act + "GET" + path_act
mac_a = hmac.new(secret_key.encode('utf-8'), msg_act.encode('utf-8'), hashlib.sha256)
sign_a = base64.b64encode(mac_a.digest()).decode('utf-8')
headers_a = {
    'ACCESS-KEY': api_key,
    'ACCESS-SIGN': sign_a,
    'ACCESS-TIMESTAMP': t_act,
    'ACCESS-PASSPHRASE': passphrase,
    'Content-Type': 'application/json',
    'locale': 'en-US'
}
r_a = requests.get(url_base + path_act, headers=headers_a, timeout=5)
data_a = r_a.json().get("data", [])
usdt_acc = next((a for a in data_a if a.get("marginCoin") == "USDT"), {})
equity = float(usdt_acc.get("usdtEquity", 0))
bal = float(usdt_acc.get("available", 0))
print(f"Day 2 Clean Cash Equity: ${equity:,.2f} USDT")