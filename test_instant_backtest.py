import time, json, os, pickle, bisect
from datetime import datetime
from backtest_engine import CACHE_FILE, get_session_key_and_name

# Pre-load & cache unified ticks in RAM
with open(CACHE_FILE, "rb") as f:
    raw_sdata = pickle.load(f)

unified_ticks = []
seen_ts = set()
for s_k, ticks in raw_sdata.items():
    for r in ticks:
        ts = r.get('ts', 0.0)
        if ts not in seen_ts:
            seen_ts.add(ts)
            unified_ticks.append(r)
unified_ticks.sort(key=lambda x: x['ts'])
all_ts = [x['ts'] for x in unified_ticks]

print(f"Pre-cached {len(unified_ticks):,} ticks in RAM.")

# Now test a slicing + simulation run
with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

start_ts = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp()
end_ts = datetime.now().timestamp()

t0 = time.time()
idx_start = bisect.bisect_left(all_ts, start_ts)
idx_end = bisect.bisect_right(all_ts, end_ts)
slice_ticks = unified_ticks[idx_start:idx_end]
t1 = time.time()
print(f"Binary search slice ({len(slice_ticks):,} ticks): {t1 - t0:.5f} sec")