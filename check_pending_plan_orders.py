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
path_plan = "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss"
t_plan = str(int(time.time() * 1000))
msg_plan = t_plan + "GET" + path_plan
mac_p = hmac.new(secret_key.encode('utf-8'), msg_plan.encode('utf-8'), hashlib.sha256)
sign_p = base64.b64encode(mac_p.digest()).decode('utf-8')
headers_p = {
    'ACCESS-KEY': api_key,
    'ACCESS-SIGN': sign_p,
    'ACCESS-TIMESTAMP': t_plan,
    'ACCESS-PASSPHRASE': passphrase,
    'Content-Type': 'application/json',
    'locale': 'en-US'
}
r_p = requests.get(url_base + path_plan, headers=headers_p, timeout=5)
print(json.dumps(r_p.json(), indent=2, ensure_ascii=False))