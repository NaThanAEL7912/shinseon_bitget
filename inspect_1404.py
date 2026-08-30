import csv

path = r'C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-21\orderflow_history_2026-08-21.csv'

rows = []
with open(path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        if len(r) >= 12 and '14:04:' in r[0]:
            rows.append(r)

print(f'Total rows at 14:04: {len(rows)}')
for r in rows[20:45]:
    # Timestamp, Price, Liq, LongLiq, ShortLiq, LiqThres, OISpeed, OIThres, 1mDelta, Slope, Signal, State
    print(f'[{r[0]}] Price: {r[1]} | OI: {r[6]} (th:{r[7]}) | Delta: {r[8]} | Slope: {r[9]} | OrigSignal: {r[10]}')