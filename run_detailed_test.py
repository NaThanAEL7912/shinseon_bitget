import json
from datetime import datetime, timedelta
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Run full period
start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)
trades = res.get("trade_logs", [])

out = []
out.append("================================================================================")
out.append(">>> [V7.26 V2.55 4대 매트릭스 엔진] 일자별 및 최근 3일 상세 실측 테스트 성과표 <<<")
out.append("================================================================================")
out.append(f"• 전체 성과: {res['total_trades']}전 {res['total_wins']}승 {res['total_losses']}패 (승률: {res['win_rate']:.1f}%) | 순수익: ${res['total_net']:+,.2f} | MDD: {res['mdd_pct']:.1f}%\n")

# Group by day
by_day = {}
for t in trades:
    day_str = t["entry_time"][:10]
    if day_str not in by_day:
        by_day[day_str] = {"trades": 0, "wins": 0, "losses": 0, "net": 0.0, "gross": 0.0}
    by_day[day_str]["trades"] += 1
    if t["is_win"]:
        by_day[day_str]["wins"] += 1
    else:
        by_day[day_str]["losses"] += 1
    by_day[day_str]["net"] += t["net"]
    by_day[day_str]["gross"] += t.get("gross", 0.0)

out.append("[📅 일자별 상세 성적표]")
for d_str in sorted(by_day.keys()):
    d = by_day[d_str]
    wr = (d["wins"] / d["trades"] * 100) if d["trades"] > 0 else 0
    net_str = f"+${d['net']:>9,.2f}" if d['net'] >= 0 else f"-${abs(d['net']):>9,.2f}"
    out.append(f"  • [{d_str}] {d['trades']:>2}전 {d['wins']:>2}승 {d['losses']:>2}패 (승률: {wr:>5.1f}%) | 순손익: {net_str}")

out.append("\n[🔍 최근 3일(8/22 ~ 8/24) 모든 개별 매매 팩트 일지]")
recent_trades = [t for t in trades if t["entry_time"] >= "2026-08-22"]
for i, t in enumerate(recent_trades):
    win_tag = "✅ 익절" if t["is_win"] else "❌ 손절"
    out.append(f"  {i+1:2d}. [{t['entry_time']}] {t['dir']:<5} | {win_tag} | 이유: {t['reason']:<16} | 순익: ${t['net']:>+8,.1f} | MAE: {t.get('min_pnl_pct', 0.0):>+5.2f}%")

with open("test_detailed_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("SAVED_DETAILED_TEST")