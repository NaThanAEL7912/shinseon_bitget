import csv

path = r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-21\orderflow_history_2026-08-21.csv"

rows = []
with open(path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        if len(r) >= 12:
            rows.append(r)

prices = [float(r[1]) for r in rows]
price_5s_ago = []
for i in range(len(prices)):
    lookback = max(0, i - 5)
    price_5s_ago.append(prices[lookback])

def test_deadband(th_val):
    signals = []
    f_pending = 'NONE'
    f_count = 0
    f_current = 'NONE'
    
    for i, r in enumerate(rows):
        p = prices[i]
        p_5s = price_5s_ago[i]
        delta_5s = p - p_5s
        
        liq = float(r[2])
        liq_th = float(r[5])
        oi = float(r[6])
        oi_th = float(r[7])
        slope_1m = float(r[9])
        
        cond_met = (liq >= liq_th) and (abs(oi) >= oi_th)
        sig = 'NONE'
        if cond_met:
            if oi > 0:
                if delta_5s >= th_val and slope_1m >= 0:
                    sig = 'LONG'
                elif delta_5s <= -th_val and slope_1m <= 0:
                    sig = 'SHORT'
            elif oi < 0:
                if delta_5s >= 10.0:
                    sig = 'LONG'
                elif delta_5s <= -10.0:
                    sig = 'SHORT'
        
        # Debounce 2s
        if sig != f_current:
            if sig == f_pending:
                f_count += 1
                if f_count >= 2:
                    f_current = sig
                    f_pending = 'NONE'
                    f_count = 0
            else:
                f_pending = sig
                f_count = 1
        else:
            f_pending = 'NONE'
            f_count = 0
        signals.append(f_current)
    
    # Calculate stats
    flips = 0
    total_signals = sum(1 for s in signals if s != 'NONE')
    for j in range(1, len(signals)):
        if signals[j] != signals[j-1] and signals[j] != 'NONE' and signals[j-1] != 'NONE':
            flips += 1
    return total_signals, flips

print("\n=== [5초 가격 델타 임계치(Deadband) 크기별 정밀 벤치마크 (50,894개 틱)] ===")
print("{:<15} | {:<18} | {:<16} | {:<20}".format("임계치(Deadband)", "총 유효 신호 틱수", "신호 급반전(Flip)", "평가"))
print("-" * 75)

for val in [3.0, 5.0, 10.0, 15.0, 20.0, 30.0]:
    tot, fl = test_deadband(val)
    eval_str = ""
    if val == 5.0:
        eval_str = "미세 잡음 잔존"
    elif val == 10.0:
        eval_str = "V자 반등($10)과 통일 (추천)"
    elif val == 15.0:
        eval_str = "황금 밸런스 (강력 추천!)"
    elif val == 20.0:
        eval_str = "초강력 고래 돌파만 포착"
    elif val >= 30.0:
        eval_str = "신호 둔화 위험"
    print("{:<15} | {:<18} | {:<16} | {:<20}".format(f"+-${val:.1f}", f"{tot}개", f"{fl}회", eval_str))