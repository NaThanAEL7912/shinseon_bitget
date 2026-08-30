import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Let us test why trades was 65
start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)
print(f"Result -> Trades: {res['total_trades']}, Wins: {res['total_wins']} ({res['win_rate']:.1f}%), Net: ${res['total_net']:+,.2f}, MDD: {res['mdd_pct']:.1f}%")