with open("docs/shinseon_whitepaper_20260818.html", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
headers = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', code)
print("SECTIONS IN 20260818:")
for h in headers[:25]:
    print(" -", re.sub('<[^<]+?>', '', h))
print(f"Total Length: {len(code)} characters")