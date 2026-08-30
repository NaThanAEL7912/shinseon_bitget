import json, copy
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

# Test Faster Scalp Targets: TP1 0.25%, TP2 0.50%
scalp_cfg = copy.deepcopy(cfg)
for s_k in scalp_cfg.get("guardrails", {}):
    if isinstance(scalp_cfg["guardrails"][s_k], dict):
        scalp_cfg["guardrails"][s_k]["tp1"] = 0.25
        scalp_cfg["guardrails"][s_k]["tp2"] = 0.50

res = run_backtest_simulation(scalp_cfg, start_dt, end_dt)
trades = res["trade_logs"]

durations = []
for t in trades:
    try:
        e = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S")
        x = datetime.strptime(t["exit_time"], "%Y-%m-%d %H:%M:%S")
        durations.append((x - e).total_seconds() / 60.0)
    except:
        pass

avg_dur = sum(durations)/len(durations) if durations else 0
fast_trades = [d for d in durations if d <= 10.0]

out = []
out.append("=== [빠른 초단타 익절 (TP1 0.25% / TP2 0.50%) 시뮬레이션 결과] ===")
out.append(f"• 총 거래수: {res['total_trades']}회 | 승리: {res['total_wins']}회 | 승률: {res['win_rate']:.1f}%")
out.append(f"• 최종 순수익: ${res['total_net']:,.2f} (ROI: {res['roi']:+.1f}%) | MDD: {res['mdd_pct']:.1f}%")
out.append(f"• 평균 포지션 보유 시간: {avg_dur:.1f}분 (10분 이내 종료율: {len(fast_trades)/len(durations)*100:.1f}%)")

with open("fast_scalp_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))