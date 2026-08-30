entry_p = 78286.07
qty = 0.1973
half_1 = 0.0986
half_2 = 0.0987
lev = 30

tp1 = 78490.0
tp2 = 78880.0
tp3 = 79950.0

targets = [
    ("1. 1st TP (Weekly High 78.5K Resistance)", tp1, half_1),
    ("2. 2nd TP (Major Box High 78.9K)", tp2, half_2),
    ("3. 3rd Mega TP (80K Round Number Squeeze)", tp3, qty)
]

print("=== LONG TP TARGET SIMULATION (Entry $78,286.07) ===")
for name, p, q in targets:
    diff = p - entry_p
    pct = (diff / entry_p) * 100.0
    roe = pct * lev
    pnl = diff * q
    print(f"- {name:<40} | Target: ${p:,.1f} | Gain: +{pct:.2f}% | ROE: +{roe:.1f}% | Profit: +${pnl:,.2f} USDT")