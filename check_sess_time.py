with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "def get_current_session" in l or "asia" in l and "09" in l:
        for j in range(max(0, i-2), min(len(lines), i+30)):
            print(f"L{j+1}: {lines[j].rstrip()}")
        break