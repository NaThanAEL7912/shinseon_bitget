import os, glob, csv, datetime

csv_files = sorted(glob.glob(r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-*\orderflow_history_*.csv"))
csv_files = [f for f in csv_files if "복사본" not in f]

def test_us_tuning(sl_pct=-0.80, liq_val=800000.0, max_daily_loss_cnt=2):
    total_t = 0
    total_w = 0
    total_l = 0
    total_net = 0.0
    
    for fpath in csv_files:
        day_str = os.path.basename(fpath).replace("orderflow_history_", "").replace(".csv", "")
        rows = []
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try: next(reader)
            except: continue
            for r in reader:
                if len(r) >= 11: rows.append(r)
        if not rows: continue
        
        prices = [float(r[1]) for r in rows]
        n = len(rows)
        
        in_pos = False
        pos_side = ""
        entry_p = 0.0
        entry_t = 0
        is_half = False
        cooldown = 0
        daily_losses = 0
        
        deb_p = 'NONE'
        deb_c = 0
        deb_curr = 'NONE'
        
        for i in range(5, n):
            if daily_losses >= max_daily_loss_cnt:
                # Daily loss limit triggered: halt for the rest of US session that night
                break
                
            r = rows[i]
            t_str = r[0].replace('="', '').replace('"', '')
            try:
                time_part = t_str.split(' ')[1]
                hh, mm, ss = map(int, time_part.split(':'))
                cur_min = hh * 60 + mm
            except: continue
            
            is_us = (cur_min >= 1290) or (cur_min < 300)
            if not is_us: continue
            
            p = prices[i]
            delta_5s = p - prices[i-5]
            try:
                liq = float(r[2])
                oi = float(r[6])
                slope = float(r[9]) if len(r) > 9 else 0.0
            except: continue
            
            cond = (liq >= liq_val) and (abs(oi) >= 0.2000)
            raw_sig = 'NONE'
            if cond:
                db = max(10.0, p * 0.0002)
                if oi > 0:
                    if delta_5s >= db and slope >= 0.0: raw_sig = 'LONG'
                    elif delta_5s <= -db and slope <= 0.0: raw_sig = 'SHORT'
                elif oi < 0:
                    if delta_5s >= db: raw_sig = 'LONG'
                    elif delta_5s <= -db: raw_sig = 'SHORT'
                    
            if raw_sig != deb_curr:
                if raw_sig == deb_p:
                    deb_c += 1
                    if deb_c >= 2:
                        deb_curr = raw_sig
                        deb_p = 'NONE'
                        deb_c = 0
                else:
                    deb_p = raw_sig
                    deb_c = 1
            else:
                deb_p = 'NONE'
                deb_c = 0
            final_sig = deb_curr
            
            if in_pos:
                pnl_pct = (p - entry_p)/entry_p*100.0 if pos_side == 'LONG' else (entry_p - p)/entry_p*100.0
                elapsed = i - entry_t
                
                if not is_half and pnl_pct >= 1.20:
                    is_half = True
                    total_net += (1.20 * 30.0 * 0.5) - 0.6
                    
                is_exit = False
                exit_roe = 0.0
                if pnl_pct >= 1.50:
                    is_exit = True
                    exit_roe = 45.0 if not is_half else 22.5
                    cooldown = i + 15
                elif pnl_pct <= sl_pct: # SL
                    is_exit = True
                    exit_roe = (sl_pct * 30.0) if not is_half else (sl_pct * 15.0)
                    cooldown = i + 60
                elif is_half and pnl_pct <= 1.00:
                    is_exit = True
                    exit_roe = 15.0
                    cooldown = i + 15
                elif elapsed >= 60 and final_sig != 'NONE' and final_sig != pos_side:
                    is_exit = True
                    exit_roe = (pnl_pct * 30.0) if not is_half else (pnl_pct * 15.0)
                    cooldown = i + 30
                    
                if is_exit:
                    fee = 2.4 if not is_half else 1.2
                    t_net = exit_roe - fee
                    total_net += t_net
                    total_t += 1
                    if t_net > 0: total_w += 1
                    else:
                        total_l += 1
                        daily_losses += 1
                    in_pos = False
                    is_half = False
            else:
                if i >= cooldown and final_sig in ['LONG', 'SHORT']:
                    in_pos = True
                    pos_side = final_sig
                    entry_p = p
                    entry_t = i
                    is_half = False
                    
    wr = (total_w / total_t * 100.0) if total_t > 0 else 0.0
    return total_t, total_w, total_l, wr, total_net

print("\n=== [US SESSION OPTIMIZATION EXPERIMENT (미장 최적화 실험)] ===")
print("{:<30} | {:<10} | {:<12} | {:<12} | {:<15}".format("Condition", "Trades", "Win/Loss", "WinRate", "Net ROE (30x)"))
print("-" * 85)

t, w, l, wr, net = test_us_tuning(sl_pct=-1.30, liq_val=800000.0, max_daily_loss_cnt=99)
print("{:<30} | {:>8} 회 | {:>2}W / {:>2}L   | {:>10.1f}% | {:>+13.2f}% ROE (현재 UI 설정)".format("현재 UI 설정 (SL -1.3%, 무제한)", t, w, l, wr, net))

t, w, l, wr, net = test_us_tuning(sl_pct=-0.80, liq_val=800000.0, max_daily_loss_cnt=99)
print("{:<30} | {:>8} 회 | {:>2}W / {:>2}L   | {:>10.1f}% | {:>+13.2f}% ROE".format("손절선 -0.8%로 축소", t, w, l, wr, net))

t, w, l, wr, net = test_us_tuning(sl_pct=-0.80, liq_val=800000.0, max_daily_loss_cnt=2)
print("{:<30} | {:>8} 회 | {:>2}W / {:>2}L   | {:>10.1f}% | {:>+13.2f}% ROE (추천: 2연패 락다운)".format("손절 -0.8% + 당일 2연패 락다운", t, w, l, wr, net))

t, w, l, wr, net = test_us_tuning(sl_pct=-0.80, liq_val=1200000.0, max_daily_loss_cnt=2)
print("{:<30} | {:>8} 회 | {:>2}W / {:>2}L   | {:>10.1f}% | {:>+13.2f}% ROE (초고래 $1.2M 필터)".format("청산 $1.2M + 손절-0.8% + 2연패락", t, w, l, wr, net))