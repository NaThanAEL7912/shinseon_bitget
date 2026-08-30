# -*- coding: utf-8 -*-
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

cmd = "grep '2026-08-18 02:20' /home/ubuntu/shinseon_server.log || true; grep '2026-08-18 02:21' /home/ubuntu/shinseon_server.log || true"
res = subprocess.run(['ssh', '-i', 'shinseon-key.pem', '-o', 'StrictHostKeyChecking=no', 'ubuntu@13.192.187.244', cmd], capture_output=True)
print("=== Server logs from 02:20:00 to 02:21:59 ===")
print(res.stdout.decode('utf-8', errors='ignore'))
