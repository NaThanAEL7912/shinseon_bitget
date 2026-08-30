import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)
trades = res.get("trade_logs", [])

strat_stats = {}
for t in trades:
    sn = t.get("strategy", "미지정")
    if sn not in strat_stats:
        strat_stats[sn] = {"trades": 0, "wins": 0, "losses": 0, "net": 0.0}
    strat_stats[sn]["trades"] += 1
    if t["is_win"]:
        strat_stats[sn]["wins"] += 1
    else:
        strat_stats[sn]["losses"] += 1
    strat_stats[sn]["net"] += t["net"]

out = []
out.append("=== [V7.26 V2.55 4대 매트릭스 전략별 상세 실측 통계] ===")
for sn, d in sorted(strat_stats.items(), key=lambda x: -x[1]["trades"]):
    wr = (d["wins"] / d["trades"] * 100) if d["trades"] > 0 else 0
    out.append(f"• {sn}")
    out.append(f"  -> 총 {d['trades']}전 {d['wins']}승 {d['losses']}패 (승률: {wr:.1f}%) | 순수익: ${d['net']:+,.2f}")

with open("strat_breakdown.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("SAVED_STRAT_BREAKDOWN")