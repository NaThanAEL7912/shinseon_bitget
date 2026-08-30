with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i in range(2595, min(2660, len(lines))):
    print(f"{i+1}: {lines[i].rstrip()}")