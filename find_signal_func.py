with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'def process_1m_data', text)]
for idx in matches:
    line_no = text[:idx].count('\n') + 1
    print(f"Found process_1m_data at Line {line_no}")