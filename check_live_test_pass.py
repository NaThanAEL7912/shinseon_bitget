import requests

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))

entry_p = 78337.60
qty = 0.1777
lev = 30
pnl_usd = (mark_p - entry_p) * qty
roe_pct = (mark_p - entry_p) / entry_p * 100.0 * lev

print(f"Current BTC Price: ${mark_p:,.2f}")
print(f"Long Entry: ${entry_p:,.2f}")
print(f"PnL: ${pnl_usd:+.2f} USDT (ROE: {roe_pct:+.2f}%)")

r_c1 = requests.get("https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=1m&limit=3", timeout=5).json()
c1 = r_c1.get('data', [])
print("\nRecent 3 1m Candles:")
for c in c1[:3]:
    vol = float(c[5])
    o, h, l, cl = float(c[1]), float(c[2]), float(c[3]), float(c[4])
    print(f"  O:${o:,.1f} | H:${h:,.1f} | L:${l:,.1f} | C:${cl:,.1f} | Vol:{vol:.2f} BTC")