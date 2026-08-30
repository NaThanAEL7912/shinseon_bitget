import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_config.json", "r", encoding="utf-8") as f:
    live_cfg = json.load(f)

# Convert live_cfg to backtest_cfg format
cfg = {
    "start_date": "2026-08-10 00:00:00",
    "end_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "initial_balance": 18000.0,
    "fee_rate": 0.0004,
    "sessions": live_cfg.get("session_thresholds", {}),
    "trading": live_cfg.get("session_trading_configs", {}),
    "guardrails": live_cfg.get("session_guardrails", {})
}

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)
print(f"Live Config Simulation -> Trades: {res['total_trades']}, Wins: {res['total_wins']} ({res['win_rate']:.2f}%), Net: ${res['total_net']:+,.2f} (ROI: {res['roi']:+.2f}%), MDD: {res['mdd_pct']:.2f}%")