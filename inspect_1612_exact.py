with open("downloads/2026-08-24/orderflow_history_2026-08-24.csv", "r", encoding="utf-8") as fp:
    lines = fp.readlines()

for l in lines:
    if "16:11:" in l or "16:12:" in l or "16:13:" in l or "16:14:" in l:
        print(l.strip())