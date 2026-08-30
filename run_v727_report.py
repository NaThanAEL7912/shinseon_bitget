import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Sync with standard config
start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)

out = []
out.append("================================================================================")
out.append(">>> [V7.27 청산 주도권 코어 완벽 원복] 14일간 전수 시뮬레이션 성적표 <<<")
out.append("================================================================================")
out.append(f"• 분석 기간: 2026-08-10 ~ 현재")
out.append(f"• 시작 원금: {res['initial_balance']:,.2f} USDT")
out.append(f"• 최종 잔고: {res['final_balance']:,.2f} USDT")
out.append(f"• 총 거래수: {res['total_trades']}전 {res['total_wins']}승 {res['total_losses']}패")
out.append(f"• 최종 승률: {res['win_rate']:.2f}% 🏆")
out.append(f"• 최종 순수익: ${res['total_net']:+,.2f} USDT (ROI: {res['roi']:+.2f}%) 🚀")
out.append(f"• 최대 낙폭 (MDD): {res['mdd_pct']:.2f}% (${res['mdd_usdt']:,.2f})")
out.append(f"• 손익비 (PF): {res['profit_factor']:.2f}")
out.append("================================================================================")
out.append("--- [8대 세션별 성과] ---")
for s_k, s_d in res.get('session_summary', {}).items():
    if s_d['trades'] > 0:
        out.append(f"  • [{s_d['name']:<14}] {s_d['trades']:>2}회 ({s_d['wins']}승 {s_d['losses']}패 | 승률: {s_d['win_rate']:>5.1f}%) | Net: ${s_d['net']:>+9,.2f} (ROI: {s_d['roi']:>+7.2f}%)")

with open("v727_final_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("SAVED_V727_REPORT")