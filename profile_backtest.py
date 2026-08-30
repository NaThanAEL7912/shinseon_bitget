import time, json
from datetime import datetime
from backtest_engine import load_all_session_data, run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

t0 = time.time()
res = run_backtest_simulation(cfg, start_dt, end_dt)
t1 = time.time()
print(f"Full backtest simulation time: {t1 - t0:.3f} seconds")
print(f"Trades: {res['total_trades']}, Win rate: {res['win_rate']:.1f}%, Net: ${res['total_net']:,.2f}")