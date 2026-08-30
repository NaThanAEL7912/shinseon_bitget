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

# Check active position
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
btc_pos = next((p for p in data_p if p.get("symbol") == "BTCUSDT" and float(p.get("total", 0)) > 0), None)

if btc_pos:
    side = btc_pos.get('holdSide')
    total = float(btc_pos.get('total', 0))
    entry = float(btc_pos.get('openPriceAvg', 0))
    lev = btc_pos.get('leverage')
    liq_p = float(btc_pos.get('liquidationPrice', 0))
    pnl = float(btc_pos.get('unrealizedPL', 0))
    print(f"Active Position: {side.upper()} {total} BTC @ ${entry:,.2f} ({lev}x)")
    print(f"Est. Liquidation Price: ${liq_p:,.2f}")
    print(f"Current Unrealized PnL: ${pnl:+.2f} USDT")
else:
    print("No active BTC position found!")

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))
print(f"Current BTC Price: ${mark_p:,.2f}")