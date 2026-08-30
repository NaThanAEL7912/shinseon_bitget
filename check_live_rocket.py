import requests

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))

entry_p = 78286.07
qty = 0.1973
lev = 30
pnl_usd = (mark_p - entry_p) * qty
roe_pct = (mark_p - entry_p) / entry_p * 100.0 * lev

print(f"Current BTC Price: ${mark_p:,.2f}")
print(f"Entry Price: ${entry_p:,.2f}")
print(f"Current Long PnL: ${pnl_usd:+.2f} USDT (ROE: {roe_pct:+.2f}%)")