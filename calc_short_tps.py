import requests

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))

entry_p = 77695.55
qty = 0.2165
lev = 30

tp1_price = 77440.0   # 5m 보라색 MA25 & 15m 노란색 MA7 지지선
tp2_price = 77220.0   # 1시간봉 MA25 메인 중심선
tp3_price = 76520.0   # 오늘의 찐바닥 (76.5K)

targets = [
    ("1. 1st Safe TP (5m/15m MA Support)", tp1_price, 0.1082),
    ("2. 2nd Main TP (1-Hour MA Centerline)", tp2_price, 0.1083),
    ("3. 3rd Moonshot TP (Today Floor 76.5K)", tp3_price, qty)
]

print(f"Current BTC Mark Price: ${mark_p:,.2f}")
print(f"Short Entry Price: ${entry_p:,.2f}")
print("=== SHORT TP TARGET SIMULATION ===")
for name, p, q in targets:
    diff = entry_p - p
    pct = (diff / entry_p) * 100.0
    roe = pct * lev
    pnl_usd = diff * q
    print(f"- {name:<35} | Target: ${p:,.1f} | Drop: -{pct:.2f}% | ROE (30x): +{roe:.1f}% | Profit: +${pnl_usd:,.2f} USDT")