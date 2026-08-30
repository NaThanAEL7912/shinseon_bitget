# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

cmd = """
python3 -c "
import glob, csv

# Check both 2026-08-17 after 21:40 KST (12:40 UTC) and 2026-08-18 all day
v625_signals = []
for fpath in glob.glob('/home/ubuntu/docs/historical_data/*.csv') + glob.glob('/home/ubuntu/*.csv'):
    if '2026-08-17' in fpath or '2026-08-18' in fpath:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 11:
                    ts = row[0].replace('=', '').replace('\"', '')
                    sig = row[10] if len(row) > 10 else ''
                    # If time is 2026-08-17 21:40:00 KST or later (or 2026-08-18)
                    if (ts >= '2026-08-17 21:40:00' and '2026-08-17' in ts) or ('2026-08-18' in ts):
                        if sig in ['LONG', 'SHORT']:
                            v625_signals.append((ts, sig, row))

print(f'Signals under Pure +OI (V6.25+) after 21:40 KST: {len(v625_signals)}')
for s in v625_signals:
    print(s)
"
"""

res = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', cmd], capture_output=True)
print(res.stdout.decode('utf-8', errors='ignore'))
