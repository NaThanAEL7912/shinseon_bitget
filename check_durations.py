import json
from datetime import datetime
from backtest_engine import run_backtest_simulation

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

start_dt = datetime.strptime("2026-08-10 00:00:00", "%Y-%m-%d %H:%M:%S")
end_dt = datetime.now()

res = run_backtest_simulation(cfg, start_dt, end_dt)
trade_logs = res["trade_logs"]

durations = []
for t in trade_logs:
    try:
        e = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S")
        x = datetime.strptime(t["exit_time"], "%Y-%m-%d %H:%M:%S")
        dur_min = (x - e).total_seconds() / 60.0
        durations.append((dur_min, t["is_win"], t["reason"], t.get("min_pnl_pct", 0.0), t.get("peak_pnl_pct", 0.0), t["entry_time"], t["exit_time"]))
    except:
        pass

durations.sort(key=lambda x: x[0], reverse=True)

out = []
out.append("=== 전수 68회 매매 포지션 보유 시간(물려있는 시간) 정밀 조사 ===")
out.append(f"총 매매 수: {len(durations)}회")

long_holds = [d for d in durations if d[0] >= 30.0]
out.append(f"• 30분 이상 장기 보유(물림) 매매: {len(long_holds)}회 / {len(durations)}회 ({len(long_holds)/len(durations)*100:.1f}%)")

buckets = {
    "0 ~ 5분 이내 (초단타 초고속 완료)": 0,
    "5 ~ 15분 (일반 파도)": 0,
    "15 ~ 30분 (중기 파도)": 0,
    "30 ~ 60분 (1시간 물림 고통 구간)": 0,
    "60분(1시간) 이상 초장기 물림": 0
}

for d in durations:
    m = d[0]
    if m <= 5: buckets["0 ~ 5분 이내 (초단타 초고속 완료)"] += 1
    elif m <= 15: buckets["5 ~ 15분 (일반 파도)"] += 1
    elif m <= 30: buckets["15 ~ 30분 (중기 파도)"] += 1
    elif m <= 60: buckets["30 ~ 60분 (1시간 물림 고통 구간)"] += 1
    else: buckets["60분(1시간) 이상 초장기 물림"] += 1

out.append("\n[보유 시간대별 분포]")
for k, v in buckets.items():
    out.append(f"  • {k}: {v}회 ({v/len(durations)*100:.1f}%)")

out.append("\n[가장 오래 물려있었던 TOP 5 매매]")
for i, d in enumerate(durations[:5]):
    win_str = "승리(익절)" if d[1] else "패배(손절)"
    out.append(f"  TOP {i+1}: {d[0]:.1f}분 ({int(d[0]//60)}시간 {int(d[0]%60)}분) | {win_str} | 사유: {d[2]} | 진입: {d[5]} -> 청산: {d[6]} | MAE: {d[3]:.2f}%")

with open("duration_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("SAVED_DURATION_REPORT")