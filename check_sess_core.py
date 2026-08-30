with open("core_logic.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
for m in re.finditer(r'session', code, re.IGNORECASE):
    idx = m.start()
    print(code[max(0, idx-50):min(len(code), idx+150)])
    print("="*40)