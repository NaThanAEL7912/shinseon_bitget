import os
import glob

print("====================================================")
print("🔍 2026-08-11 03:36:54 KST 진입 원인 정밀 수색 팩트")
print("====================================================")

# Find all log files
log_files = glob.glob('/home/ubuntu/*.log') + glob.glob('/home/ubuntu/logs/*.log') + glob.glob('/home/ubuntu/*.txt')

for lf in log_files:
    print(f"\n📁 [LOG FILE]: {lf}")
    try:
        with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        matched = [l.strip() for l in lines if '03:36' in l or '03:35' in l or '03:37' in l or '03:34' in l or '03:38' in l]
        print(f"   Matches count: {len(matched)}")
        for m in matched[:40]:
            print("  ", m)
    except Exception as e:
        print("   Error reading log:", e)

# Find csv files
csv_files = glob.glob('/home/ubuntu/*.csv') + glob.glob('/home/ubuntu/data/*.csv')
for cf in csv_files:
    print(f"\n📊 [CSV FILE]: {cf}")
    try:
        with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        matched = [l.strip() for l in lines if '03:36' in l or '03:35' in l or '03:37' in l or '2026-08-11 03:3' in l]
        print(f"   Matches count: {len(matched)}")
        for m in matched[:20]:
            print("  ", m)
    except Exception as e:
        print("   Error reading csv:", e)
