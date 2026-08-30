# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

cmd = """
python3 -c "
import csv

# 1. Check 2026-08-17 from 17:00:00 to 23:59:59
signals_17 = []
with open('/home/ubuntu/docs/historical_data/orderflow_history_2026-08-17.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.reader(f)
    header = next(reader, None)
    for row in reader:
        if len(row) >= 11:
            ts = row[0].replace('=', '').replace('\"', '')
            if ts >= '2026-08-17 17:00:00':
                sig = row[10]
                if sig in ['LONG', 'SHORT']:
                    signals_17.append((ts, sig, row[1], row[2], row[6], row[9]))

print(f'=== 2026-08-17 (17:00 ~ 24:00 KST) Signal Count: {len(signals_17)} ===')
for s in signals_17[:10]:
    print(f' - Time: {s[0]} | Signal: {s[1]} | BTC: ${s[2]} | Liq: ${s[3]} | OI: {s[4]}% | Slope: {s[5]}')
if len(signals_17) > 10:
    print(f' ... and {len(signals_17)-10} more')

# 2. Check 2026-08-18 from 00:00:00 to now
signals_18 = []
with open('/home/ubuntu/docs/historical_data/orderflow_history_2026-08-18.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.reader(f)
    header = next(reader, None)
    for row in reader:
        if len(row) >= 11:
            ts = row[0].replace('=', '').replace('\"', '')
            sig = row[10]
            if sig in ['LONG', 'SHORT']:
                signals_18.append((ts, sig, row[1], row[2], row[6], row[9]))

print(f'\n=== 2026-08-18 (00:00 ~ 02:38 KST) Signal Count: {len(signals_18)} ===')
for s in signals_18[:10]:
    print(f' - Time: {s[0]} | Signal: {s[1]} | BTC: ${s[2]} | Liq: ${s[3]} | OI: {s[4]}% | Slope: {s[5]}')
if len(signals_18) > 10:
    print(f' ... and {len(signals_18)-10} more')
"
"""

res = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', cmd], capture_output=True)
print(res.stdout.decode('utf-8', errors='ignore'))
