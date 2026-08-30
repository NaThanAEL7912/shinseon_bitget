import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# 1. 22일간 (08-03 ~ 08-24)
start_22d = datetime.strptime("2026-08-03 00:00:00", "%Y-%m-%d %H:%M:%S")
end_22d = datetime.strptime("2026-08-24 23:59:59", "%Y-%m-%d %H:%M:%S")
res_22d = run_backtest_simulation(cfg, start_22d, end_22d)
print(f"[22일간 8/3~8/24] Trades: {res_22d['total_trades']}, Wins: {res_22d['total_wins']} ({res_22d['win_rate']:.1f}%), Net: ${res_22d['total_net']:+,.2f}")

# 2. 14일간 (08-10 ~ 08-24)
start_14d = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_14d = datetime.strptime("2026-08-24 23:59:59", "%Y-%m-%d %H:%M:%S")
res_14d = run_backtest_simulation(cfg, start_14d, end_14d)
print(f"[14일간 8/10~8/24] Trades: {res_14d['total_trades']}, Wins: {res_14d['total_wins']} ({res_14d['win_rate']:.1f}%), Net: ${res_14d['total_net']:+,.2f}")