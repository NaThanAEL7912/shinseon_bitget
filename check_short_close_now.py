import requests

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))

entry_p = 77702.1
qty = 0.1146
lev = 30

# For short: profit = (entry - mark) * qty
pnl_usd = (entry_p - mark_p) * qty
pnl_pct = (entry_p - mark_p) / entry_p * 100.0
roe_pct = pnl_pct * lev

print(f"Current BTC Mark Price: ${mark_p:,.2f}")
print(f"Short Entry Price: ${entry_p:,.2f}")
print(f"Diff: {mark_p - entry_p:+.2f} USD")
print(f"Current PnL: ${pnl_usd:+.2f} USDT (ROE: {roe_pct:+.2f}%)")