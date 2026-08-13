with open('/home/ubuntu/logs/shinseon_trade_2026-08-11.log', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("=== 03:36:00 ~ 03:37:00 로그 팩트 100% 인쇄 ===")
for idx, l in enumerate(lines):
    if '03:36:' in l or '03:37:0' in l or '03:37:1' in l:
        if any(keyword in l for keyword in ['진입', 'SHORT', 'LONG', '청산', 'TRADE', 'TELEGRAM', '사유', 'OI', 'liq', '신호', '비중']):
            print(f"L{idx+1}: {l.strip()}")
