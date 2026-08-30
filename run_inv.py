import json, copy
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)
trade_logs = res["trade_logs"]
wins = [t for t in trade_logs if t["is_win"]]
losses = [t for t in trade_logs if not t["is_win"]]

out = []
out.append(f"Total trades: {len(trade_logs)}, Wins: {len(wins)} ({len(wins)/len(trade_logs)*100:.1f}%), Losses: {len(losses)}")

# Check min_pnl_pct
wins_with_dd = [t for t in wins if t.get("min_pnl_pct", 0.0) < -0.05]
out.append(f"Wins with Drawdown (< -0.05%): {len(wins_with_dd)} / {len(wins)} ({len(wins_with_dd)/len(wins)*100:.1f}%)")

buckets = {
    "0.00% to -0.10% (No Drawdown)": 0,
    "-0.10% to -0.25% (Mild Shakeout)": 0,
    "-0.25% to -0.45% (Medium Pullback / DCA zone)": 0,
    "-0.45% to -0.70% (Deep Pullback / near SL)": 0,
    "< -0.70% (Extreme)": 0
}

for t in wins:
    mae = t.get("min_pnl_pct", 0.0)
    if mae >= -0.10:
        buckets["0.00% to -0.10% (No Drawdown)"] += 1
    elif mae >= -0.25:
        buckets["-0.10% to -0.25% (Mild Shakeout)"] += 1
    elif mae >= -0.45:
        buckets["-0.25% to -0.45% (Medium Pullback / DCA zone)"] += 1
    elif mae >= -0.70:
        buckets["-0.45% to -0.70% (Deep Pullback / near SL)"] += 1
    else:
        buckets["< -0.70% (Extreme)"] += 1

out.append("\n--- Drawdown Depth of 52 Winning Trades ---")
for k, v in buckets.items():
    out.append(f"  {k}: {v} trades ({v/len(wins)*100:.1f}%)")

# Test SL sensitivity
out.append("\n--- SL Sensitivity Analysis ---")
for sl_val in [-0.20, -0.30, -0.40, -0.50, -0.60, -0.80, -1.00]:
    t_cfg = copy.deepcopy(cfg)
    for s_k in t_cfg.get("sessions", {}):
        t_cfg["sessions"][s_k]["sl"] = sl_val
    r = run_backtest_simulation(t_cfg, start_dt, end_dt)
    out.append(f"  SL {sl_val:+.2f}% -> Trades: {r['total_trades']:2d} | WinRate: {r['win_rate']:5.1f}% | Net: ${r['total_net']:+9,.2f} | ROI: {r['roi']:+6.1f}% | MDD: {r['mdd_pct']:4.1f}%")

with open("inv_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("SAVED_INV_RESULT")