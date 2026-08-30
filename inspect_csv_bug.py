with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i in range(2598, 2620):
    print(f"L{i+1}: {lines[i].rstrip()}")