import os, glob
from datetime import datetime

# Find latest CSV files or server log
today_str = datetime.now().strftime("%Y-%m-%d")
files = glob.glob(f"*{today_str}*") + glob.glob("shinseon_live_ticks*.csv") + glob.glob("*.log") + glob.glob("downloads/*/*.csv")
print("Found files:", files[:10])

# Check recent lines from downloads or live CSV
latest_csv = None
for f in sorted(glob.glob("downloads/*/*.csv"), reverse=True):
    if "2026-08-24" in f or "20260824" in f:
        latest_csv = f
        break

if latest_csv:
    print("Latest CSV:", latest_csv)
    with open(latest_csv, "r", encoding="utf-8") as fp:
        lines = fp.readlines()
        print(f"Total lines in {latest_csv}: {len(lines)}")
        # filter lines around 16:10 ~ 16:15
        recents = [l for l in lines if "16:1" in l or "16:0" in l or "15:5" in l]
        print(f"Lines around 16:xx: {len(recents)}")
        for l in recents[-15:]:
            print(l.strip())