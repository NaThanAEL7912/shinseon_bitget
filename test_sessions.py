import os, glob, csv, datetime

csv_files = sorted(glob.glob(r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-*\orderflow_history_*.csv"))
csv_files = [f for f in csv_files if "복사본" not in f]

def run_session_backtest(target_session="EUROPE", is_new=False):
    total_trades = 0
    wins = 0
    losses = 0
    gross_pnl = 0.0
    total_fees = 0.0
    net_pnl = 0.0
    
    # Session configs
    if target_session == "EUROPE":
        # 16:00 ~ 21:30 KST
        target_liq = 600000.0
        target_oi = 0.2000
        tp1_pnl = 0.50 # +15% ROE
        tp2_pnl = 1.00 # +30% ROE
        sl_pnl = -0.80 # -24% ROE
    elif target_session == "US":
        # 21:30 ~ 05:00 KST
        target_liq = 800000.0
        target_oi = 0.2000
        tp1_pnl = 0.80 # +24% ROE
        tp2_pnl = 1.50 # +45% ROE
        sl_pnl = -1.30 # -39% ROE
    else: # BOTH (EUROPE + US)
        pass

    for fpath in csv_files:
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
        entry_price = 0.0
        entry_t = 0
        is_half_tp = False
        cooldown_until = 0
        
        deb_pending = 'NONE'
        deb_count = 0
        deb_current = 'NONE'
        
        for i in range(5, n):
            r = rows[i]
            t_str = r[0].replace('="', '').replace('"', '')
            # Extract time HH:MM:SS
            try:
                time_part = t_str.split(' ')[1]
                hh, mm, ss = map(int, time_part.split(':'))
                cur_min = hh * 60 + mm
            except:
                continue
                
            # Filter session
            is_in_target = False
            cur_liq_th = 600000.0
            cur_oi_th = 0.2000
            cur_tp1 = 0.50
            cur_tp2 = 1.00
            cur_sl = -0.80
            
            # Europe: 16:00 (960m) <= t < 21:30 (1290m)
            is_europe = (960 <= cur_min < 1290)
            # US: 21:30 (1290m) <= t <= 23:59 or 00:00 <= t < 05:00 (300m)
            is_us = (cur_min >= 1290) or (cur_min < 300)
            
            if target_session == "EUROPE":
                if is_europe:
                    is_in_target = True
                    cur_liq_th = 600000.0
                    cur_oi_th = 0.2000
                    cur_tp1 = 0.50
                    cur_tp2 = 1.00
                    cur_sl = -0.80
            elif target_session == "US":
                if is_us:
                    is_in_target = True
                    cur_liq_th = 800000.0
                    cur_oi_th = 0.2000
                    cur_tp1 = 0.80
                    cur_tp2 = 1.50
                    cur_sl = -1.30
            elif target_session == "COMBINED":
                if is_europe:
                    is_in_target = True
                    cur_liq_th = 600000.0
                    cur_oi_th = 0.2000
                    cur_tp1 = 0.50
                    cur_tp2 = 1.00
                    cur_sl = -0.80
                elif is_us:
                    is_in_target = True
                    cur_liq_th = 800000.0
                    cur_oi_th = 0.2000
                    cur_tp1 = 0.80
                    cur_tp2 = 1.50
                    cur_sl = -1.30
            
            p = prices[i]
            p_5s = prices[i-5]
            delta_5s = p - p_5s
            
            try:
                liq = float(r[2])
                oi = float(r[6])
                slope_1m = float(r[9]) if len(r) > 9 else 0.0
            except: continue
            
            cond_met = is_in_target and (liq >= cur_liq_th) and (abs(oi) >= cur_oi_th)
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
                roe_pct = pnl_pct * 30.0
                elapsed_sec = i - entry_t
                
                # 1. 50% TP check
                if not is_half_tp and pnl_pct >= cur_tp1:
                    is_half_tp = True
                    gross_pnl += (cur_tp1 * 30.0 * 0.5)
                    total_fees += 0.6
                
                # 2. Final Exit check
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
                elif is_half_tp and pnl_pct <= 0.10:
                    is_exit = True
                    exit_roe = 1.5
                    cooldown_until = i + 15
                elif elapsed_sec >= 60 and final_sig != 'NONE' and final_sig != pos_side:
                    is_exit = True
                    exit_roe = roe_pct if not is_half_tp else (roe_pct * 0.5)
                    cooldown_until = i + 30
                    
                if is_exit:
                    fee_rt = 2.4 if not is_half_tp else 1.2
                    net_trade = exit_roe - fee_rt
                    gross_pnl += exit_roe
                    total_fees += fee_rt
                    net_pnl += net_trade
                    total_trades += 1
                    if net_trade > 0: wins += 1
                    else: losses += 1
                    in_pos = False
                    is_half_tp = False
            else:
                if is_in_target and i >= cooldown_until and final_sig in ['LONG', 'SHORT']:
                    in_pos = True
                    pos_side = final_sig
                    entry_price = p
                    entry_t = i
                    is_half_tp = False
                    
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    return {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "gross_roe": gross_pnl,
        "fees": total_fees,
        "net_roe": net_pnl
    }

eur_old = run_session_backtest("EUROPE", False)
eur_new = run_session_backtest("EUROPE", True)

us_old = run_session_backtest("US", False)
us_new = run_session_backtest("US", True)

comb_old = run_session_backtest("COMBINED", False)
comb_new = run_session_backtest("COMBINED", True)

lines = []
lines.append("=" * 85)
lines.append(">>> [EUROPE & US SESSION SPECIALIZED 13-DAY BACKTEST REPORT] <<<")
lines.append("    - Europe: 16:00~21:30 KST (Liq >= $600K, OI >= 0.20%, SL -0.8%, TP 50% +0.5%)")
lines.append("    - US NY : 21:30~05:00 KST (Liq >= $800K, OI >= 0.20%, SL -1.3%, TP 50% +0.8%)")
lines.append("=" * 85)
lines.append(f"{'Session / Metric':<30} | {'[Old Engine V6.73]':<22} | {'[New 0.02% Engine V6.87]':<26}")
lines.append("-" * 85)

lines.append("[1. EUROPE SESSION (16:00 ~ 21:30 KST)]")
lines.append(f"  - Total Trades               | {eur_old['trades']:>18} 회 | {eur_new['trades']:>22} 회")
lines.append(f"  - Win / Loss                 | {eur_old['wins']}W / {eur_old['losses']}L              | {eur_new['wins']}W / {eur_new['losses']}L")
lines.append(f"  - Win Rate (%)               | {eur_old['win_rate']:>17.2f} % | {eur_new['win_rate']:>21.2f} % [WIN]")
lines.append(f"  - Total Fees (ROE)           | {eur_old['fees']:>15.2f} % ROE | {eur_new['fees']:>19.2f} % ROE")
lines.append(f"  - Net Cumulative ROE (%)     | {eur_old['net_roe']:>+15.2f} % ROE | {eur_new['net_roe']:>+19.2f} % ROE [UP]")

lines.append("-" * 85)
lines.append("[2. US REGULAR SESSION (21:30 ~ 05:00 KST)]")
lines.append(f"  - Total Trades               | {us_old['trades']:>18} 회 | {us_new['trades']:>22} 회")
lines.append(f"  - Win / Loss                 | {us_old['wins']}W / {us_old['losses']}L              | {us_new['wins']}W / {us_new['losses']}L")
lines.append(f"  - Win Rate (%)               | {us_old['win_rate']:>17.2f} % | {us_new['win_rate']:>21.2f} % [WIN]")
lines.append(f"  - Total Fees (ROE)           | {us_old['fees']:>15.2f} % ROE | {us_new['fees']:>19.2f} % ROE")
lines.append(f"  - Net Cumulative ROE (%)     | {us_old['net_roe']:>+15.2f} % ROE | {us_new['net_roe']:>+19.2f} % ROE [UP]")

lines.append("-" * 85)
lines.append("[3. GOLDEN TIME COMBINED (EUROPE + US NY)]")
lines.append(f"  - Total Trades               | {comb_old['trades']:>18} 회 | {comb_new['trades']:>22} 회")
lines.append(f"  - Win Rate (%)               | {comb_old['win_rate']:>17.2f} % | {comb_new['win_rate']:>21.2f} % [WIN]")
lines.append(f"  - Net Cumulative ROE (%)     | {comb_old['net_roe']:>+15.2f} % ROE | {comb_new['net_roe']:>+19.2f} % ROE [UP]")
lines.append("=" * 85)

print("\n".join(lines))