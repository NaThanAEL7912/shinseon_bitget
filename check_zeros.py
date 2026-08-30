import csv

path = r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-20\orderflow_history_2026-08-20.csv"
zero_count = 0
with open(path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        if len(r) >= 2 and float(r[1]) <= 1000.0:
            zero_count += 1

print(f"Total rows with price <= 1000 (corrupt/zero price during server reboot/WSS reconnect): {zero_count}")