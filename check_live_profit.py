import requests

r = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r['data'][0].get('markPrice', 0))

entry_p = 76973.2
qty = 0.1371
lev = 30

pnl_usd = (mark_p - entry_p) * qty
pnl_pct = (mark_p - entry_p) / entry_p * 100.0
roe_pct = pnl_pct * lev

print(f"Current BTC Price: ${mark_p:,.2f}")
print(f"Entry Price: ${entry_p:,.2f}")
print(f"Gain: {pnl_pct:+.2f}% (ROE 30x: {roe_pct:+.2f}%)")
print(f"Unrealized Profit: +${pnl_usd:,.2f} USDT")