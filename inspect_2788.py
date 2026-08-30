with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i in range(2780, min(2800, len(lines))):
    print(f"L{i+1}: {lines[i].rstrip()}")