path = "docs/프로젝트_버전_관리.md"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_entry = "| V6.90 | 2026-08-21 16:12 | 잔여 1.0205 BTC 롱 포지션 $75,600 익절보장 트레일링 스탑 선주문 정격 발주 완료 | docs/기획서_280_잔여1.0205BTC_익절보장_트레일링스탑_발주.md |\n"

# Insert after header table row (line 3)
lines.insert(3, new_entry)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("VERSION_LOG_UPDATED_V6.90")