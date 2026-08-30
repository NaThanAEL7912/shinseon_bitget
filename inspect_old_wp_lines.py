with open("docs/shinseon_whitepaper_20260818.html", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "<h" in l:
        print(f"L{i+1}: {l.strip()[:80].encode('ascii', errors='replace').decode()}")