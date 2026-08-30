import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Let us verify what threshold produced 65 trades
for test_liq in [250000, 400000, 500000, 600000]:
    for test_oi in [0.04, 0.05, 0.10, 0.15]:
        test_cfg = json.loads(json.dumps(cfg))
        # if using uniform or session
        res = run_backtest_simulation(test_cfg, datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S"), datetime.now())
        print(f"Current backtest_config -> Trades: {res['total_trades']}, Wins: {res['total_wins']} ({res['win_rate']:.1f}%), Net: ${res['total_net']:+,.2f}")
        break
    break