with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
for m in re.finditer(r'def get_.*session.*\(', code):
    start = m.start()
    print(code[start:start+1000])