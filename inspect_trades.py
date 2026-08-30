# -*- coding: utf-8 -*-
import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)

lines = []
lines.append(f"Total trades: {res['total_trades']}, Win rate: {res['win_rate']:.1f}%, Net: ${res['total_net']:,.2f}")
lines.append("\n--- First 15 trades detail ---")
for i, t in enumerate(res['trade_logs'][:15]):
    lines.append(f"[{i+1}] {t['entry_time']} -> {t['exit_time']} | {t['dir']} | {t['strategy']} | PnL: {t['pnl_pct']:+.2f}% (${t['net_pnl']:+,.2f}) | Exit: {t['reason']}")

with open("trade_inspect_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("DONE")