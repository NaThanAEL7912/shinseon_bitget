with open('/home/ubuntu/docs/historical_data/orderflow_history_2026-08-11.csv', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("=== Header ===")
print(lines[0].strip())

print("\n=== 03:36:30 ~ 03:37:05 1초 단위 CSV 데이터 실측 팩트 ===")
for idx, line in enumerate(lines):
    if '03:36:' in line or '03:37:0' in line:
        print(f"L{idx+1}: {line.strip()}")
