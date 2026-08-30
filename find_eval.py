with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "evaluate_orderflow_signal" in l or "target_liq" in l or "abs(oi_delta_1m)" in l:
        print(f"L{i+1}: {l.strip()[:90]}")