entry_p = 78337.60
qty = 0.1777
lev = 30
target_82k = 82000.0

diff_82k = target_82k - entry_p
pct_82k = (diff_82k / entry_p) * 100.0
roe_82k = pct_82k * lev
profit_82k = diff_82k * qty
won_krw = int(profit_82k * 1380)

print(f"Target 82k: ${target_82k:,.1f}")
print(f"Gain: +{pct_82k:.2f}% | ROE (30x): +{roe_82k:.1f}%")
print(f"Profit USD: +${profit_82k:,.2f} USDT")
print(f"Profit KRW: 약 {won_krw:,} 원")