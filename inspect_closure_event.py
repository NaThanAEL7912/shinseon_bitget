# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Search for 02:21 logs
cmd = "grep '2026-08-18 02:2' /home/ubuntu/shinseon_server.log"
res = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', cmd], capture_output=True)
print("=== [1] Logs from 02:20 to 02:29 ===")
lines = res.stdout.decode('utf-8', errors='ignore').splitlines()
for line in lines[-50:]:
    print(line)

# 2. Search for STOP_LOSS or CLEAR or takeProfit or stopLoss in the entire log
cmd2 = "grep -E 'STOP_LOSS|CLEAR|손절|익절|스탑|포지션' /home/ubuntu/shinseon_server.log | tail -n 30"
res2 = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', cmd2], capture_output=True)
print("\n=== [2] Position Exit Events ===")
print(res2.stdout.decode('utf-8', errors='ignore'))
