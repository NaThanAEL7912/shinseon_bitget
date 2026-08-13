import re

with open('/home/ubuntu/shinseon_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()

print("====================================================")
print("🔍 AWS 서버 (shinseon_server.py) 주문 관련 실측 팩트 검증")
print("====================================================")

# 1. VERSION CHECK
ver_matches = [l.strip() for l in lines if 'CURRENT_VERSION' in l or 'V5.58' in l or 'V5.5' in l]
print("📌 [1. SERVER VERSION FACT]")
for v in ver_matches[:5]:
    print("  ", v)

# 2. MARGIN MODE CHECK
print("\n📌 [2. MARGIN MODE FACT]")
margin_matches = [(i+1, l.strip()) for i, l in enumerate(lines) if 'marginMode' in l or 'margin_mode' in l]
for idx, l in margin_matches:
    print(f"   Line {idx}: {l}")

# 3. CLOSE SIDE & PARTIAL CLOSE CHECK
print("\n📌 [3. PARTIAL CLOSE & CLOSE_SIDE FACT]")
partial_matches = [(i+1, l.strip()) for i, l in enumerate(lines) if 'close_side' in l or 'PARTIAL_CLOSE' in l or '50_PERCENT_CLOSE' in l]
for idx, l in partial_matches:
    print(f"   Line {idx}: {l}")

# 4. TELEGRAM AFTER EXECUTION CHECK
print("\n📌 [4. TELEGRAM ALERT AFTER EXECUTION FACT]")
tg_matches = [(i+1, l.strip()) for i, l in enumerate(lines) if 'send_telegram_msg' in l or '분할익절 알림' in l]
for idx, l in tg_matches:
    print(f"   Line {idx}: {l}")
