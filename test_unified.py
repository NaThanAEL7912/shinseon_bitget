import pickle
from datetime import datetime

with open('scratch/parsed_session_data.pkl', 'rb') as f:
    raw = pickle.load(f)

unified = []
seen = set()
for k, rows in raw.items():
    for r in rows:
        ts = r['ts']
        if ts not in seen:
            seen.add(ts)
            unified.append(r)
unified.sort(key=lambda x: x['ts'])

print(f"Total unified ticks: {len(unified):,}")
print(f"Start: {datetime.fromtimestamp(unified[0]['ts'])}")
print(f"End: {datetime.fromtimestamp(unified[-1]['ts'])}")