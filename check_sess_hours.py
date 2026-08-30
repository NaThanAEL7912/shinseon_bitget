with open("core_logic.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "session" in line.lower() and ("hour" in line.lower() or "09" in line or "16" in line or "22" in line or "weekday" in line):
        print(f"L{idx+1}: {line.strip()[:100]}")