import os, glob, csv, datetime

csv_files = sorted(glob.glob(r"C:\Working\AntiGravity\ShinSeon_Bitget\downloads\2026-08-*\orderflow_history_*.csv"))
csv_files = [f for f in csv_files if "복사본" not in f]

# Let's inspect US session day by day
print("=== [US SESSION DAY-BY-DAY BREAKDOWN (21:30 ~ 05:00 KST)] ===")
print("{:<12} | {:<10} | {:<10} | {:<12} | {:<15}".format("Date", "Trades", "Win/Loss", "WinRate", "Net ROE (30x)"))
print("-" * 65)

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
    
    trades = 0
    wins = 0
    losses = 0
    net_roe = 0.0
    
    deb_p = 'NONE'
    deb_c = 0
    deb_curr = 'NONE'
    
    for i in range(5, n):
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
        
        cond = (liq >= 800000.0) and (abs(oi) >= 0.2000)
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
                net_roe += (1.20 * 30.0 * 0.5) - 0.6
                
            is_exit = False
            exit_roe = 0.0
            if pnl_pct >= 1.50:
                is_exit = True
                exit_roe = 45.0 if not is_half else 22.5
                cooldown = i + 15
            elif pnl_pct <= -1.30: # SL -1.3%
                is_exit = True
                exit_roe = -39.0 if not is_half else -19.5
                cooldown = i + 60
            elif is_half and pnl_pct <= 1.00:
                is_exit = True
                exit_roe = 15.0 # 1.00 * 30 * 0.5
                cooldown = i + 15
            elif elapsed >= 60 and final_sig != 'NONE' and final_sig != pos_side:
                is_exit = True
                exit_roe = (pnl_pct * 30.0) if not is_half else (pnl_pct * 15.0)
                cooldown = i + 30
                
            if is_exit:
                fee = 2.4 if not is_half else 1.2
                t_net = exit_roe - fee
                net_roe += t_net
                trades += 1
                if t_net > 0: wins += 1
                else: losses += 1
                in_pos = False
                is_half = False
        else:
            if i >= cooldown and final_sig in ['LONG', 'SHORT']:
                in_pos = True
                pos_side = final_sig
                entry_p = p
                entry_t = i
                is_half = False
                
    wr_str = f"{(wins/trades*100.0):.1f}%" if trades > 0 else "0.0%"
    print("{:<12} | {:>8} 회 | {:>2}W / {:>2}L   | {:>10} | {:>+13.2f}% ROE".format(
        day_str, trades, wins, losses, wr_str, net_roe
    ))