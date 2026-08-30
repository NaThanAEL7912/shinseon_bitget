# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

def run_ssh(remote_cmd):
    res = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', remote_cmd], capture_output=True)
    return res.stdout.decode('utf-8', errors='ignore')

print("1. Searching 2026-08-17 (17:00 ~ 23:59:59 KST)...")
out17_long = run_ssh("grep ',LONG,' /home/ubuntu/docs/historical_data/orderflow_history_2026-08-17.csv")
lines17_long = [l for l in out17_long.splitlines() if any(l.startswith(f'="2026-08-17 {h:02d}:') for h in range(17, 24))]
print(f" - 17:00 이후 LONG 신호 개수: {len(lines17_long)}")
for l in lines17_long[:5]:
    print("   " + l)

out17_short = run_ssh("grep ',SHORT,' /home/ubuntu/docs/historical_data/orderflow_history_2026-08-17.csv")
lines17_short = [l for l in out17_short.splitlines() if any(l.startswith(f'="2026-08-17 {h:02d}:') for h in range(17, 24))]
print(f" - 17:00 이후 SHORT 신호 개수: {len(lines17_short)}")
for l in lines17_short[:5]:
    print("   " + l)

print("\n2. Searching 2026-08-18 (00:00 ~ 02:40 KST)...")
out18_long = run_ssh("grep ',LONG,' /home/ubuntu/docs/historical_data/orderflow_history_2026-08-18.csv")
print(f" - 오늘(08-18) LONG 신호 개수: {len(out18_long.splitlines())}")
for l in out18_long.splitlines()[:5]:
    print("   " + l)

out18_short = run_ssh("grep ',SHORT,' /home/ubuntu/docs/historical_data/orderflow_history_2026-08-18.csv")
print(f" - 오늘(08-18) SHORT 신호 개수: {len(out18_short.splitlines())}")
for l in out18_short.splitlines()[:5]:
    print("   " + l)
