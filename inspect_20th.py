import csv

path = r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-20\orderflow_history_2026-08-20.csv"
rows = []
with open(path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        if len(r) >= 11:
            rows.append(r)

prices = [float(r[1]) for r in rows]
print(f"Total rows on 2026-08-20: {len(rows)}")
print(f"Min Price: {min(prices)} | Max Price: {max(prices)} | Start: {prices[0]} | End: {prices[-1]}")