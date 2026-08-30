with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
matches = [l for l in code.splitlines() if "session" in l.lower() or "아시아" in l or "유럽" in l or "미국" in l]
for m in matches[:15]:
    print(m)