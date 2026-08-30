entry_p = 76910.0
targets = [
    ("1. Europe Main 78K Target", 77950.0),
    ("2. Weekend Top Resistance", 78450.0),
    ("3. Weekly Range High Resistance", 79150.0),
    ("4. 80K Mega Squeeze Level", 79950.0)
]

print("=== HIGHER TARGET SIMULATION (Entry $76,910) ===")
for name, price in targets:
    pnl = (price - entry_p) / entry_p * 100.0
    roe = pnl * 30.0
    print(f"- {name:<30}: ${price:,.1f} | Gain: {pnl:+.2f}% | ROE (30x): {roe:+.1f}%")