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

# Check positions
path_pos = "/api/v2/mix/position/all-position?productType=USDT-FUTURES"
t_pos = str(int(time.time() * 1000))
msg_pos = t_pos + "GET" + "/api/v2/mix/position/all-position" + "?" + "productType=USDT-FUTURES"
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
r_p = requests.get(url_base + "/api/v2/mix/position/all-position?productType=USDT-FUTURES", headers=headers_p, timeout=5)
data_p = r_p.json().get("data", [])
active = [p for p in data_p if float(p.get("total", 0)) > 0]

print("=== ACTIVE POSITIONS ===")
for p in active:
    print(f"- {p.get('symbol')} {p.get('holdSide')} {p.get('total')} BTC @ ${p.get('openPriceAvg')} | PnL: ${float(p.get('unrealizedPL', 0)):+.2f}")

# Check account balance
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
print(f"\nTotal USDT Equity: ${equity:,.2f}")
print(f"Available Balance: ${bal:,.2f}")

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))
print(f"Current BTC Price: ${mark_p:,.2f}")