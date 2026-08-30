with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
matches = re.findall(r'/api/v2/mix/order/[a-zA-Z0-9\-_?=&]+', code)
for m in set(matches):
    print(m)