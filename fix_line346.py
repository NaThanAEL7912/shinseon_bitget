with open('core_logic.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'poison_status=' in l:
        lines[i] = '                        poison_status="기각: 슬리피지 초과" if (random.random() < 0.015 and not self.v35_engine.is_position_active) else "정상 가동 중",\n'

with open('core_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Line 346 fixed successfully")
