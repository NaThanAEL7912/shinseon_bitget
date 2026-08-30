import re, sys

log_file = '/home/ubuntu/logs/shinseon_trade_2026-08-20.log'
print("=== ANALYZING shinseon_trade_2026-08-20.log ===")
try:
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

print(f"Total lines in trade log: {len(lines)}")

# Let's inspect price drops and OI deltas
events = []
for line in lines:
    if "DELEVERAGING" in line or "BEARISH" in line or "SHORT" in line or "1분 OI" in line:
        events.append(line.strip())

print(f"Found {len(events)} matching event lines")
for e in events[:5]:
    print("  [Sample Start]", e[:120])
for e in events[-5:]:
    print("  [Sample End]", e[:120])