import re

with open('core_logic.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # Check for unterminated quotes or broken multi-byte chars
    # If line has odd number of quotes and ends abruptly
    single_q = line.count("'")
    double_q = line.count('"')
    if (single_q % 2 != 0 or double_q % 2 != 0) and ('ui_callback' in line or 'poison_status' in line or 'current_session' in line):
        # Fix line 564
        if '564' in str(i+1) or 'ui_callback' in line:
            line = '                        ui_callback(self.current_price, 0, "🟢 [안내] 하이브리드 프리미엄 엔진 가동 중...", current_session="안전 가동 중")\n'
    new_lines.append(line)

with open('core_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("core_logic.py cleaned")
