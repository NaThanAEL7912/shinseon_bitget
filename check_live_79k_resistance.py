import json, requests

# 1. Check live position
entry_p = 78641.56
qty = 0.4357
lev = 60

r_t = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
mark_p = float(r_t['data'][0].get('markPrice', 0))
pnl_usd = (mark_p - entry_p) * qty
roe_pct = (mark_p - entry_p) / entry_p * 100.0 * lev

print(f"Current BTC Price: ${mark_p:,.2f}")
print(f"Long Entry Price: ${entry_p:,.2f}")
print(f"Current Long PnL: ${pnl_usd:+.2f} USDT (ROE: {roe_pct:+.2f}%)")

# 2. Check Orderbook asks around 79000
r_ob = requests.get("https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=BTCUSDT&productType=USDT-FUTURES&limit=15", timeout=5).json()
ob_data = r_ob.get("data", {})
asks = ob_data.get("asks", [])
bids = ob_data.get("bids", [])

print("\n=== ORDERBOOK ASKS (Resistance Wall around 79,000) ===")
sum_ask = 0
for a in asks[:8]:
    p, q = float(a[0]), float(a[1])
    sum_ask += q
    print(f"  Ask Price: ${p:,.1f} | Qty: {q:.2f} BTC | Cumulative: {sum_ask:.2f} BTC")

# 3. Check 15m candles
r_c1 = requests.get("https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=15m&limit=4", timeout=5).json()
c1 = r_c1.get('data', [])
print("\nRecent 4 15m Candles:")
for c in c1[:4]:
    vol = float(c[5])
    o, h, l, cl = float(c[1]), float(c[2]), float(c[3]), float(c[4])
    print(f"  O:${o:,.1f} | H:${h:,.1f} | L:${l:,.1f} | C:${cl:,.1f} | Vol:{vol:.1f} BTC")