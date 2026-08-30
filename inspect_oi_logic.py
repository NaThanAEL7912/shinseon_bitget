with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    code = f.read()

import re
# Find all occurrences of target_oi, oi_delta_1m, direction in shinseon_server.py
for idx, line in enumerate(code.splitlines()):
    if "oi_delta_1m" in line or "target_oi" in line or "binance_ws_frame" in line:
        if "if " in line or "elif " in line or "signal" in line:
            print(f"L{idx+1}: {line}")