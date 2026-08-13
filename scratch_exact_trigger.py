with open('/home/ubuntu/logs/shinseon_trade_2026-08-11.log', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("=== 03:36:30 ~ 03:36:56 전라인 정밀 인쇄 ===")
for idx, l in enumerate(lines):
    if any(f"03:36:{s:02d}" for s in range(30, 56)):
        print(f"L{idx+1}: {l.strip()}")
