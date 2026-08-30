# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Check CSV files on AWS for any LONG or SHORT signals after 17:00:00 KST
cmd_csv = """
python3 -c "
import glob, csv

signals = []
for fpath in glob.glob('/home/ubuntu/docs/historical_data/*.csv') + glob.glob('/home/ubuntu/*.csv'):
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 11:
                    ts = row[0]
                    # Filter for 2026-08-17 17:00:00 to now
                    if ('2026-08-17' in ts and ts >= '2026-08-17 17:00:00') or ('2026-08-18' in ts):
                        sig = row[10] if len(row) > 10 else ''
                        if sig in ['LONG', 'SHORT']:
                            signals.append((ts, sig, row))
    except Exception as e:
        pass

print(f'Total signals found in CSV after 17:00: {len(signals)}')
for s in signals:
    print(s)
"
"""

res = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', cmd_csv], capture_output=True)
print("=== [1] CSV Signal Search Result ===")
print(res.stdout.decode('utf-8', errors='ignore'))
print(res.stderr.decode('utf-8', errors='ignore'))

# 2. Check server log for any AUTO ENTRY or Signal trigger
cmd_log = """
grep -E '타점 포착|신규 진입 성공|자동 발주|신호 발생' /home/ubuntu/shinseon_server.log | grep -E '2026-08-17 1[7-9]|2026-08-17 2[0-3]|2026-08-18'
"""
res2 = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', cmd_log], capture_output=True)
print("\n=== [2] Server Log Signal/Entry Search Result ===")
print(res2.stdout.decode('utf-8', errors='ignore'))
