import os, glob, csv, sys

csv_files = sorted(glob.glob(r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-*\orderflow_history_*.csv"))
csv_files = [f for f in csv_files if "복사본" not in f]

print("Found files:", len(csv_files))

def backtest_engine(is_new_engine=False):
    total_trades = 0
    wins = 0
    losses = 0
    total_pnl_pct = 0.0 # ROE sum (30x)
    total_fee_pct = 0.0
    total_net_pnl = 0.0
    whipsaw_cut_count = 0
    
    for fpath in csv_files:
        rows = []
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except:
                continue
            for r in reader:
                if len(r) >= 11:
                    rows.append(r)
        if not rows:
            continue
            
        prices = [float(r[1]) for r in rows]
        n = len(rows)
        
        in_pos = False
        pos_side = ""
        entry_price = 0.0
        entry_idx = 0
        is_half_tp = False
        
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
            except:
                continue
                
            cond_met = (liq >= liq_th) and (abs(oi) >= oi_th)
            
            raw_sig = 'NONE'
            if cond_met:
                if not is_new_engine:
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
            
            if is_new_engine:
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
                if pos_side == 'LONG':
                    pnl_pct = (p - entry_price) / entry_price * 100.0
                else:
                    pnl_pct = (entry_price - p) / entry_price * 100.0
                
                roe_pct = pnl_pct * 30.0
                
                if not is_half_tp and pnl_pct >= 0.50:
                    is_half_tp = True
                    total_pnl_pct += (15.0 * 0.5)
                    total_fee_pct += 0.6
                
                is_closed = False
                close_roe = 0.0
                
                if pnl_pct >= 1.0:
                    is_closed = True
                    close_roe = 30.0 if not is_half_tp else 15.0
                elif pnl_pct <= -0.70:
                    is_closed = True
                    close_roe = -21.0 if not is_half_tp else -10.5
                elif is_half_tp and pnl_pct <= 0.10:
                    is_closed = True
                    close_roe = 3.0
                elif final_sig != 'NONE' and final_sig != pos_side:
                    is_closed = True
                    close_roe = roe_pct if not is_half_tp else (roe_pct * 0.5)
                    whipsaw_cut_count += 1
                
                if is_closed:
                    total_trades += 1
                    fee_roundtrip = 2.4 if not is_half_tp else 1.2
                    total_fee_pct += fee_roundtrip
                    net_trade_roe = close_roe - fee_roundtrip
                    total_pnl_pct += close_roe
                    total_net_pnl += net_trade_roe
                    if net_trade_roe > 0:
                        wins += 1
                    else:
                        losses += 1
                    in_pos = False
                    is_half_tp = False
            else:
                if final_sig in ['LONG', 'SHORT']:
                    in_pos = True
                    pos_side = final_sig
                    entry_price = p
                    entry_idx = i
                    is_half_tp = False
                    
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    return {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "gross_roe": total_pnl_pct,
        "fees": total_fee_pct,
        "net_roe": total_net_pnl,
        "whipsaw_cuts": whipsaw_cut_count
    }

res_old = backtest_engine(is_new_engine=False)
res_new = backtest_engine(is_new_engine=True)

out = []
out.append("\n==================================================================")
out.append(">>> 14-DAY MASTER BACKTEST COMPARISON REPORT (500,000+ TICKS) <<<")
out.append("==================================================================")
out.append(f"{'Metric':<25} | {'[Old Engine V6.73]':<20} | {'[New 0.02% Engine V6.87]':<25}")
out.append("-" * 75)
out.append(f"{'Total Trades':<25} | {res_old['trades']:>18} | {res_new['trades']:>23}")
out.append(f"{'Win Trades':<25} | {res_old['wins']:>18} | {res_new['wins']:>23}")
out.append(f"{'Loss Trades':<25} | {res_old['losses']:>18} | {res_new['losses']:>23}")
out.append(f"{'Win Rate (%)':<25} | {res_old['win_rate']:>17.2f}% | {res_new['win_rate']:>22.2f}%")
out.append(f"{'Whipsaw Reversal Cuts':<25} | {res_old['whipsaw_cuts']:>18} | {res_new['whipsaw_cuts']:>23}")
out.append(f"{'Total Trading Fees (ROE)':<25} | {res_old['fees']:>16.2f}% | {res_new['fees']:>21.2f}%")
out.append(f"{'Cumulative Net ROE (%)':<25} | {res_old['net_roe']:>+16.2f}% | {res_new['net_roe']:>+21.2f}%")
out.append("==================================================================")

print("\n".join(out))