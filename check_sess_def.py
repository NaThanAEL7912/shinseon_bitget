with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "session_thresholds" in l or "get_current_session" in l:
        for j in range(max(0, i-5), min(len(lines), i+25)):
            print(f"L{j+1}: {lines[j].rstrip()}")
        break