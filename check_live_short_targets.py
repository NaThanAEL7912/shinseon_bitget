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
    pnl = float(btc_pos.get('unrealizedPL', 0))
    print(f"Active Position: {side.upper()} {total} BTC @ ${entry:,.2f} ({lev}x) | PnL: ${pnl:+.2f} USDT")
else:
    print("No active BTC position found!")

# Get Current Price
r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))
print(f"Current BTC Price: ${mark_p:,.2f}")

# Check 1h & 4h major support levels
# 1차 지지선: 78,500$ (아까 뚫었던 주간 최고점 넥라인 지지대)
# 2차 지지선: 77,900$ ~ 78,000$ (1시간봉 MA25 및 78K 라운드피겨)
# 3차 지지선: 77,200$ ~ 77,300$ (오늘 낮 중심선 지지대)
# 4차 바닥: 76,500$ (오늘 최저점 대바닥)

if btc_pos and side.lower() == 'short':
    targets = [
        ("1차 안전 분할익절 (주간 넥라인 지지대)", 78500.0, total * 0.5),
        ("2차 메인 하방익절 (1시간봉 MA25 & 78K)", 77950.0, total * 0.5),
        ("3차 심야 폭포수 올킬 (오늘 낮 중심선)", 77250.0, total)
    ]
    print("\n=== SHORT TP TARGET SIMULATION ===")
    for name, p, q in targets:
        diff = entry - p
        pct = (diff / entry) * 100.0
        roe = pct * float(lev)
        pnl_val = diff * q
        print(f"- {name:<35} | Target: ${p:,.1f} | Drop: -{pct:.2f}% | ROE: +{roe:.1f}% | Profit: +${pnl_val:,.2f} USDT")