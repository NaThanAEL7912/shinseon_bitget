import os
import glob

print("=== AWS CSV FILE EXACT LINES AROUND 03:36:53 ===")
csv_files = glob.glob('/home/ubuntu/*.csv') + glob.glob('/home/ubuntu/data/*.csv') + glob.glob('/home/ubuntu/logs/*.csv')

for cf in csv_files:
    print(f"\n📊 [CSV FILE]: {cf}")
    try:
        with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        print(f"Header: {lines[0].strip() if lines else 'EMPTY'}")
        matched = [(i+1, l.strip()) for i, l in enumerate(lines) if '03:36:' in l or '03:37:0' in l]
        print(f"Matched count: {len(matched)}")
        for idx, m in matched:
            print(f"  Line {idx}: {m}")
    except Exception as e:
        print("Error reading csv:", e)
