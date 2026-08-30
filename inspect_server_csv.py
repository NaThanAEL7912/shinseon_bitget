with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
matches = re.findall(r'def\s+\w+|class\s+\w+|csv|orderflow_history|STOPPED|NONE|Signal', code)
print("Hits in shinseon_server.py:", len(matches))

# Find where orderflow_history is written
for idx, line in enumerate(code.splitlines()):
    if "orderflow_history" in line or "csv_writer" in line or "csv" in line or "STOPPED" in line:
        print(f"L{idx+1}: {line}")