import time, json, os, pickle
from datetime import datetime
from backtest_engine import CACHE_FILE, get_session_key_and_name

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Step 1: Pickle load
t0 = time.time()
with open(CACHE_FILE, "rb") as f:
    raw_sdata = pickle.load(f)
t1 = time.time()
print(f"1. Pickle load (80MB): {t1 - t0:.3f} sec")

# Step 2: Unified ticks build & sort
t0 = time.time()
unified_ticks = []
seen_ts = set()
start_ts = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp()
end_ts = datetime.now().timestamp()

for s_k, ticks in raw_sdata.items():
    for r in ticks:
        ts = r.get('ts', 0.0)
        if ts not in seen_ts and start_ts <= ts <= end_ts:
            seen_ts.add(ts)
            unified_ticks.append(r)
unified_ticks.sort(key=lambda x: x['ts'])
t1 = time.time()
print(f"2. Unified ticks ({len(unified_ticks):,} items) extract & sort: {t1 - t0:.3f} sec")

# Step 3: Simulation loop
t0 = time.time()
from backtest_engine import run_backtest_simulation
start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()
res = run_backtest_simulation(config, start_dt, end_dt)
t1 = time.time()
print(f"3. Full simulation call: {t1 - t0:.3f} sec")