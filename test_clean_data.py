import os, glob, csv, datetime

csv_files = sorted(glob.glob(r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-*\orderflow_history_*.csv"))
csv_files = [f for f in csv_files if "복사본" not in f]

def run_clean_backtest(is_new=True):
    sessions_stats = {
        "ASIA": {"trades": 0, "wins": 0, "losses": 0, "gross_pnl": 0.0, "fees": 0.0, "net_pnl": 0.0},
        "EUROPE": {"trades": 0, "wins": 0, "losses": 0, "gross_pnl": 0.0, "fees": 0.0, "net_pnl": 0.0},
        "US": {"trades": 0, "wins": 0, "losses": 0, "gross_pnl": 0.0, "fees": 0.0, "net_pnl": 0.0},
        "PACIFIC": {"trades": 0, "wins": 0, "losses": 0, "gross_pnl": 0.0, "fees": 0.0, "net_pnl": 0.0},
        "TOTAL": {"trades": 0, "wins": 0, "losses": 0, "gross_pnl": 0.0, "fees": 0.0, "net_pnl": 0.0}
    }
    daily_stats = {}
    
    for fpath in csv_files:
        day_str = os.path.basename(fpath).replace("orderflow_history_", "").replace(".csv", "")
        try:
            dt_day = datetime.datetime.strptime(day_str, "%Y-%m-%d")
            is_weekend = (dt_day.weekday() >= 5)
        except: is_weekend = False
        
        rows = []
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try: next(reader)
            except: continue
            for r in reader:
                # Filter corrupt 0.0 price rows!
                if len(r) >= 11 and float(r[1]) > 10000.0:
                    rows.append(r)
        if not rows: continue
        
        prices = [float(r[1]) for r in rows]
        n = len(rows)
        
        in_pos = False
        pos_side = ""
        pos_session = ""
        entry_price = 0.0
        entry_t = 0
        is_half_tp = False
        cooldown_until = 0
        
        cur_tp1 = 0.80
        cur_tp2 = 1.20
        cur_guard = 0.50
        cur_sl = -0.60
        
        deb_pending = 'NONE'
        deb_count = 0
        deb_current = 'NONE'
        
        day_net = 0.0
        
        for i in range(5, n):
            r = rows[i]
            t_str = r[0].replace('="', '').replace('"', '')
            try:
                time_part = t_str.split(' ')[1]
                hh, mm, ss = map(int, time_part.split(':'))
                cur_min = hh * 60 + mm
            except: continue
            
            if 300 <= cur_min < 540:
                sess_name = "PACIFIC"
                if not is_weekend: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 500000.0, 0.1200, -1.00, 0.40, 0.60, 0.20
                else: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 150000.0, 0.0300, -0.50, 0.40, 0.50, 0.10
            elif 540 <= cur_min < 960:
                sess_name = "ASIA"
                if not is_weekend: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 250000.0, 0.1500, -0.60, 0.80, 1.20, 0.50
                else: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 200000.0, 0.0400, -0.60, 0.50, 0.80, 0.10
            elif 960 <= cur_min < 1290:
                sess_name = "EUROPE"
                if not is_weekend: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 600000.0, 0.1800, -0.80, 1.00, 1.20, 0.50
                else: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 300000.0, 0.0500, -0.60, 0.40, 0.60, 0.10
            else:
                sess_name = "US"
                if not is_weekend: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 800000.0, 0.2000, -1.30, 1.20, 1.50, 1.00
                else: liq_th, oi_th, sl_th, tp1_val, tp2_val, guard_val = 500000.0, 0.0400, -0.80, 0.80, 1.20, 0.10
                
            p = prices[i]
            p_5s = prices[i-5]
            delta_5s = p - p_5s
            
            try:
                liq = float(r[2])
                oi = float(r[6])
                slope_1m = float(r[9]) if len(r) > 9 else 0.0
            except: continue
            
            cond_met = (liq >= liq_th) and (abs(oi) >= oi_th)
            raw_sig = 'NONE'
            if cond_met:
                if not is_new:
                    if oi > 0:
                        if delta_5s > 0: raw_sig = 'LONG'
                        elif delta_5s < 0: raw_sig = 'SHORT'
                    elif oi < 0:
                        if delta_5s >= 10.0: raw_sig = 'LONG'
                        elif delta_5s <= -10.0: raw_sig = 'SHORT'
                else:
                    deadband = max(10.0, p * 0.0002)
                    if oi > 0:
                        if delta_5s >= deadband and slope_1m >= 0.0: raw_sig = 'LONG'
                        elif delta_5s <= -deadband and slope_1m <= 0.0: raw_sig = 'SHORT'
                    elif oi < 0:
                        if delta_5s >= deadband: raw_sig = 'LONG'
                        elif delta_5s <= -deadband: raw_sig = 'SHORT'
                        
            if is_new:
                if raw_sig != deb_current:
                    if raw_sig == deb_pending:
                        deb_count += 1
                        if deb_count >= 2:
                            deb_current = raw_sig
                            deb_pending = 'NONE'
                            deb_count = 0
                    else:
                        deb_pending = raw_sig
                        deb_count = 1
                else:
                    deb_pending = 'NONE'
                    deb_count = 0
                final_sig = deb_current
            else:
                final_sig = raw_sig
                
            if in_pos:
                pnl_pct = (p - entry_price) / entry_price * 100.0 if pos_side == 'LONG' else (entry_price - p) / entry_price * 100.0
                elapsed_sec = i - entry_t
                
                if not is_half_tp and pnl_pct >= cur_tp1:
                    is_half_tp = True
                    earned_roe = cur_tp1 * 30.0 * 0.5
                    sessions_stats[pos_session]["gross_pnl"] += earned_roe
                    sessions_stats[pos_session]["fees"] += 0.6
                    sessions_stats["TOTAL"]["gross_pnl"] += earned_roe
                    sessions_stats["TOTAL"]["fees"] += 0.6
                    day_net += (earned_roe - 0.6)
                
                is_exit = False
                exit_roe = 0.0
                if pnl_pct >= cur_tp2:
                    is_exit = True
                    exit_roe = (cur_tp2 * 30.0) if not is_half_tp else (cur_tp2 * 30.0 * 0.5)
                    cooldown_until = i + 15
                elif pnl_pct <= cur_sl:
                    is_exit = True
                    exit_roe = (cur_sl * 30.0) if not is_half_tp else (cur_sl * 30.0 * 0.5)
                    cooldown_until = i + 60
                elif is_half_tp and pnl_pct <= cur_guard:
                    is_exit = True
                    exit_roe = (cur_guard * 30.0 * 0.5)
                    cooldown_until = i + 15
                elif elapsed_sec >= 60 and final_sig != 'NONE' and final_sig != pos_side:
                    is_exit = True
                    exit_roe = (pnl_pct * 30.0) if not is_half_tp else (pnl_pct * 15.0)
                    cooldown_until = i + 30
                    
                if is_exit:
                    fee_rt = 2.4 if not is_half_tp else 1.2
                    net_trade = exit_roe - fee_rt
                    for target_k in [pos_session, "TOTAL"]:
                        sessions_stats[target_k]["gross_pnl"] += exit_roe
                        sessions_stats[target_k]["fees"] += fee_rt
                        sessions_stats[target_k]["net_pnl"] += net_trade
                        sessions_stats[target_k]["trades"] += 1
                        if net_trade > 0: sessions_stats[target_k]["wins"] += 1
                        else: sessions_stats[target_k]["losses"] += 1
                    day_net += net_trade
                    in_pos = False
                    is_half_tp = False
            else:
                if i >= cooldown_until and final_sig in ['LONG', 'SHORT']:
                    in_pos = True
                    pos_side = final_sig
                    pos_session = sess_name
                    entry_price = p
                    entry_t = i
                    is_half_tp = False
                    cur_tp1 = tp1_val
                    cur_tp2 = tp2_val
                    cur_guard = guard_val
                    cur_sl = sl_th
        daily_stats[day_str] = day_net
        
    for k in sessions_stats:
        tr = sessions_stats[k]["trades"]
        sessions_stats[k]["win_rate"] = (sessions_stats[k]["wins"] / tr * 100.0) if tr > 0 else 0.0
    return sessions_stats, daily_stats

clean_old_stats, clean_old_daily = run_clean_backtest(is_new=False)
clean_new_stats, clean_new_daily = run_clean_backtest(is_new=True)

print("=== [CLEANED BACKTEST RESULTS (Zero-Price Artifacts Filtered)] ===")
for s in ["ASIA", "EUROPE", "US", "PACIFIC", "TOTAL"]:
    o = clean_old_stats[s]
    n = clean_new_stats[s]
    print(f"{s:<10} | Trades: {o['trades']}->{n['trades']} | WinRate: {o['win_rate']:.1f}%->{n['win_rate']:.1f}% | Net ROE: {o['net_pnl']:+.1f}%->{n['net_pnl']:+.1f}%")

print("\n=== [DAILY NET ROE ON CLEAN DATA] ===")
for d in sorted(clean_new_daily.keys()):
    print(f"{d}: Old = {clean_old_daily[d]:+.1f}% ROE | New = {clean_new_daily[d]:+.1f}% ROE")