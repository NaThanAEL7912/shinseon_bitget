import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)
trade_logs = res['trade_logs']

print(f"=== 전수 65회 매매 진입 후 역주행(마이너스) 정밀 통계 조사 ===")
total_trades = len(trade_logs)
wins = [t for t in trade_logs if t['is_win']]
losses = [t for t in trade_logs if not t['is_win']]

print(f"총 매매: {total_trades}회 | 승리: {len(wins)}회 ({len(wins)/total_trades*100:.1f}%) | 패배: {len(losses)}회")

# 1. 승리 매매 중 진입 후 마이너스를 겪은 비율
wins_with_drawdown = [t for t in wins if t.get('min_pnl_pct', 0.0) < -0.05]
print(f"\n[1. 승리한 {len(wins)}개 매매의 진입 후 마이너스(역주행) 경험 비율]")
print(f"-> 진입 후 -0.05% 이상 마이너스로 출렁였던 매매: {len(wins_with_drawdown)}회 / {len(wins)}회 ({len(wins_with_drawdown)/len(wins)*100:.1f}%)")

# 2. 승리 매매들의 최대 역주행 낙폭(MAE) 분포
mae_buckets = {
    "0.00% ~ -0.10% (거의 무조정 직행)": 0,
    "-0.10% ~ -0.25% (가벼운 잔파도)": 0,
    "-0.25% ~ -0.45% (중간 숨고르기/2차물타기권)": 0,
    "-0.45% ~ -0.70% (깊은 눌림목/손절 직전 버팀)": 0,
    "-0.70% 이하": 0
}

for t in wins:
    mae = t.get('min_pnl_pct', 0.0)
    if mae >= -0.10:
        mae_buckets["0.00% ~ -0.10% (거의 무조정 직행)"] += 1
    elif mae >= -0.25:
        mae_buckets["-0.10% ~ -0.25% (가벼운 잔파도)"] += 1
    elif mae >= -0.45:
        mae_buckets["-0.25% ~ -0.45% (중간 숨고르기/2차물타기권)"] += 1
    elif mae >= -0.70:
        mae_buckets["-0.45% ~ -0.70% (깊은 눌림목/손절 직전 버팀)"] += 1
    else:
        mae_buckets["-0.70% 이하"] += 1

print("\n[2. 승리 매매들의 최대 역주행(MAE) 깊이 분포]")
for k, v in mae_buckets.items():
    pct = v / len(wins) * 100
    print(f"  • {k}: {v}회 ({pct:.1f}%)")

# 3. 손절선(SL) 길이에 따른 승률/수익률 시뮬레이션 비교
print("\n[3. 만약 손절선을 좁혔거나 넓혔다면 어떻게 되었을까? (손절폭 민감도 조사)]")