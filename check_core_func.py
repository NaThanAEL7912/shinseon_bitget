with open("core_logic.py", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'def check_radar_signal_dynamic', text)]
for idx in matches:
    line_no = text[:idx].count('\n') + 1
    print(f"core_logic.py has check_radar_signal_dynamic at line {line_no}")