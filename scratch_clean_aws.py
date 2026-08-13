import os, glob

files = glob.glob('/home/ubuntu/logs/trade_stats_*.json') + glob.glob('/home/ubuntu/logs/trade_stats_summary.json')
for f in files:
    if os.path.exists(f):
        try:
            os.remove(f)
            print(f"REMOVED: {f}")
        except Exception as e:
            print(f"REMOVE ERR {f}: {e}")

print("Clean completed!")
