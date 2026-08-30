import os, glob, csv

csv_files = sorted(glob.glob(r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-*\orderflow_history_*.csv"))
csv_files = [f for f in csv_files if "복사본" not in f]

def run_realistic_backtest(is_new=False):
    total_trades = 0
    wins = 0
    losses = 0
    gross_pnl = 0.0
    total_fees = 0.0
    net_pnl = 0.0
    
    daily_results = {}
    
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
        entry_price = 0.0
        entry_t = 0
        is_half_tp = False
        cooldown_until = 0
        
        day_wins = 0
        day_losses = 0
        day_net = 0.0
        
        deb_pending = 'NONE'
        deb_count = 0
        deb_current = 'NONE'
        
        for i in range(5, n):
            r = rows[i]
            p = prices[i]
            p_5s = prices[i-5]
            delta_5s = p - p_5s
            
            try:
                liq = float(r[2])
                liq_th = float(r[5])
                oi = float(r[6])
                oi_th = float(r[7])
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
                roe_pct = pnl_pct * 30.0
                elapsed_sec = i - entry_t
                
                # 1. 50% TP check (+0.40% PNL = +12.0% ROE)
                if not is_half_tp and pnl_pct >= 0.40:
                    is_half_tp = True
                    gross_pnl += (12.0 * 0.5)
                    total_fees += 0.6
                
                # 2. Final Exit check
                is_exit = False
                exit_roe = 0.0
                
                if pnl_pct >= 0.80:
                    is_exit = True
                    exit_roe = 24.0 if not is_half_tp else 12.0
                    cooldown_until = i + 15
                elif pnl_pct <= -0.60:
                    is_exit = True
                    exit_roe = -18.0 if not is_half_tp else -9.0
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
                    if net_trade > 0:
                        wins += 1
                        day_wins += 1
                    else:
                        losses += 1
                        day_losses += 1
                    day_net += net_trade
                    in_pos = False
                    is_half_tp = False
            else:
                if i >= cooldown_until and final_sig in ['LONG', 'SHORT']:
                    in_pos = True
                    pos_side = final_sig
                    entry_price = p
                    entry_t = i
                    is_half_tp = False
                    
        daily_results[day_str] = {
            "wins": day_wins,
            "losses": day_losses,
            "net_roe": day_net
        }
        
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    return {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "gross_roe": gross_pnl,
        "fees": total_fees,
        "net_roe": net_pnl,
        "daily": daily_results
    }

old_res = run_realistic_backtest(is_new=False)
new_res = run_realistic_backtest(is_new=True)

lines = []
lines.append("=" * 80)
lines.append("[SHINSEON 14-DAY MASTER BACKTEST REPORT (500,000+ TICKS)]")
lines.append("=" * 80)
lines.append(f"{'Metric':<30} | {'[Old Engine V6.73]':<20} | {'[New 0.02% Engine V6.87]':<24}")
lines.append("-" * 80)
lines.append(f"{'Total Trades':<30} | {old_res['trades']:>18} | {new_res['trades']:>22}")
lines.append(f"{'Win Trades':<30} | {old_res['wins']:>18} | {new_res['wins']:>22}")
lines.append(f"{'Loss Trades':<30} | {old_res['losses']:>18} | {new_res['losses']:>22}")
lines.append(f"{'Win Rate (%)':<30} | {old_res['win_rate']:>17.2f}% | {new_res['win_rate']:>21.2f}%")
lines.append(f"{'Total Fees/Slippage (ROE)':<30} | {old_res['fees']:>16.2f}% | {new_res['fees']:>20.2f}%")
lines.append(f"{'Fee Reduction Saved':<30} | {'-':>18} | {old_res['fees'] - new_res['fees']:>+19.2f}% Saved!")
lines.append(f"{'Cumulative Net ROE (%)':<30} | {old_res['net_roe']:>+16.2f}% | {new_res['net_roe']:>+20.2f}%")
lines.append("=" * 80)

lines.append("\n[Daily Breakdown Comparison]")
lines.append(f"{'Date':<12} | {'[Old Net ROE]':<18} | {'[New 0.02% Net ROE]':<22} | {'Improvement'}")
lines.append("-" * 75)
for d in sorted(old_res['daily'].keys()):
    o_net = old_res['daily'][d]['net_roe']
    n_net = new_res['daily'][d]['net_roe']
    diff = n_net - o_net
    lines.append(f"{d:<12} | {o_net:>+14.2f}% ROE | {n_net:>+18.2f}% ROE | {diff:>+10.2f}%")
lines.append("=" * 75)

print("\n".join(lines))