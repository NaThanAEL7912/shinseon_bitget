with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "current_session_key" in line or "session_key" in line or "asia" in line.lower() and "hour" in line.lower():
        print(f"L{idx+1}: {line.strip()[:100]}")