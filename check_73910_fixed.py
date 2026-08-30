with open("downloads/2026-08-21/orderflow_history_2026-08-21_NEW.csv", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i in range(73905, 73918):
    if i < len(lines):
        print(f"L{i+1}: {lines[i].strip()}")