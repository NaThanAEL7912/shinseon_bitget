import requests

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))

entry_p = 78771.57
qty = 0.7321
lev = 120
pnl_usd = (mark_p - entry_p) * qty
roe_pct = (mark_p - entry_p) / entry_p * 100.0 * lev

target_100p = entry_p + (100.0 / qty)
target_150p = entry_p + (150.0 / qty)

print(f"Current BTC Price: ${mark_p:,.2f}")
print(f"Long Entry Price: ${entry_p:,.2f}")
print(f"Current Long PnL: ${pnl_usd:+.2f} USDT (ROE: {roe_pct:+.2f}%)")
print(f"Price for +$100 PnL: ${target_100p:,.2f} (Distance: ${target_100p - mark_p:+.2f})")
print(f"Price for +$150 PnL: ${target_150p:,.2f} (Distance: ${target_150p - mark_p:+.2f})")