with open("docs/SHINSEON_오더플로우_판단_백서_20260817.md", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

print("20260817 MD Length:", len(text))
print("First 1000 chars:")
print(text[:1000].encode('ascii', errors='replace').decode())