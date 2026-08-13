with open('/home/ubuntu/logs/shinseon_trade_2026-08-11.log', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("=== LINES 26320 to 26355 EXPLICIT PRINT ===")
for i in range(26320, 26356):
    if i < len(lines):
        print(f"L{i+1}: {lines[i].strip()}")
