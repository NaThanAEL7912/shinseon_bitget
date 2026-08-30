import time, math
from datetime import datetime

# Benchmark 1: datetime.fromtimestamp
ts = 1787490000.0
t0 = time.time()
for _ in range(1000000):
    dt = datetime.fromtimestamp(ts)
    w = dt.weekday()
    h = dt.hour
    m = dt.minute
t1 = time.time()
print(f"1M datetime.fromtimestamp: {t1 - t0:.3f} sec")

# Benchmark 2: Fast integer math
t0 = time.time()
for _ in range(1000000):
    kst_sec = int(ts + 32400)
    day_sec = kst_sec % 86400
    h = day_sec // 3600
    m = (day_sec % 3600) // 60
    w = ((kst_sec // 86400) + 3) % 7
t1 = time.time()
print(f"1M fast integer math: {t1 - t0:.3f} sec")