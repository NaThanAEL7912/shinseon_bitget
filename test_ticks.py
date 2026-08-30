import json, math, time
from datetime import datetime
from backtest_engine import load_all_session_data, get_session_key_and_name

raw_sdata = load_all_session_data()
unified_ticks = []
seen_ts = set()
for s_k, ticks in raw_sdata.items():
    for r in ticks:
        ts = r.get("ts", 0.0)
        if ts not in seen_ts:
            seen_ts.add(ts)
            unified_ticks.append(r)
unified_ticks.sort(key=lambda x: x["ts"])
print(f"Total unified ticks loaded: {len(unified_ticks):,}")