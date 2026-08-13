import os
import glob

print("=== 2026-08-11 03:36 PRECISION SEARCH ===")

files = glob.glob('/home/ubuntu/logs/*.log') + glob.glob('/home/ubuntu/*.log')
for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f):
                if '2026-08-11 03:36:' in line or '2026-08-11 03:35:' in line or '2026-08-11 03:37:' in line or '03:36:54' in line or '03:36:38' in line:
                    print(f"[{os.path.basename(fpath)}:{idx+1}] {line.strip()}")
    except Exception as e:
        pass
