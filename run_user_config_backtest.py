# -*- coding: utf-8 -*-
import json, sys
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open('shinseon_backtest_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)

if 'error' in res:
    print('ERROR:', res['error'])
    sys.exit(1)

out = []
out.append('=' * 80)
out.append('>>> [SHINSEON V7.17] 8-SESSION CONTINUOUS BACKTEST REPORT <<<')
out.append('=' * 80)
out.append(f"분석 기간 (Period):     2026-08-10 00:00:00 ~ 현재")
out.append(f"시작 원금 (Initial):     {res['initial_balance']:,.2f} USDT")
out.append(f"최종 잔고 (Final):       {res['final_balance']:,.2f} USDT")
out.append(f"총 거래 횟수 (Trades):   {res['total_trades']}회 ({res['total_wins']}승 {res['total_losses']}패)")
out.append(f"승률 (Win Rate):         {res['win_rate']:.2f}%")
out.append(f"수수료전 총수익 (Gross): +${res['total_gross']:,.2f}")
out.append(f"총 지불 수수료 (Fee):   -${res['total_fee']:,.2f}")
net_str = f"+${res['total_net']:,.2f}" if res['total_net'] >= 0 else f"-${abs(res['total_net']):,.2f}"
out.append(f"최종 실질 순수익 (Net):  {net_str}")
out.append(f"계좌 수익률 (ROI):       {res['roi']:+.2f}%")
out.append(f"최대 낙폭 (MDD):         {res['mdd_pct']:.2f}% (${res['mdd_usdt']:,.2f})")
out.append(f"손익비 (Profit Factor):  {res['profit_factor']:.2f}")
out.append('=' * 80)
out.append('--- [8대 세션별 상세 성과표] ---')
for s_k, s_d in res['session_summary'].items():
    if s_d['trades'] > 0:
        s_net_str = f"+${s_d['net']:,.2f}" if s_d['net'] >= 0 else f"-${abs(s_d['net']):,.2f}"
        out.append(f"[{s_d['name']:<14}] {s_d['trades']:>2}회 ({s_d['wins']}승 {s_d['losses']}패 | 승률: {s_d['win_rate']:>5.1f}%) | Gross: +${s_d['gross']:>9.2f} | Fee: -${s_d['fee']:>8.2f} | Net: {s_net_str:>11} (ROI: {s_d['roi']:>+7.2f}%)")

reasons = {}
for t in res.get('trade_logs', []):
    r = t.get('reason', '')
    reasons[r] = reasons.get(r, 0) + 1

out.append('\n--- [청산 사유별 통계] ---')
for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
    out.append(f"  - {r}: {c}회")

res_text = "\n".join(out)
with open('backtest_run_output.txt', 'w', encoding='utf-8') as f:
    f.write(res_text)

print("SUCCESS_WRITTEN")