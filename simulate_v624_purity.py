# -*- coding: utf-8 -*-
import glob, os, csv

csv_files = sorted(glob.glob('/home/ubuntu/docs/historical_data/orderflow_history_2026-08-1[34567].csv'))

def run_strategy(only_pos_oi=True):
    total_trades = 0
    wins = 0
    losses = 0
    total_pnl = 0.0
    
    for fpath in csv_files:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            rows = list(reader)
            
            i = 0
            while i < len(rows):
                row = rows[i]
                if len(row) < 11:
                    i += 1
                    continue
                try:
                    price = float(row[1])
                    oi = float(row[6])
                    sig = row[10].strip()
                except:
                    i += 1
                    continue
                    
                if sig in ['LONG', 'SHORT']:
                    is_pos = (oi > 0)
                    if only_pos_oi and not is_pos:
                        i += 1
                        continue
                        
                    entry_p = price
                    direction = sig
                    total_trades += 1
                    
                    # Track trade outcome with V6.24 rules:
                    # SL: -1.3%, TP: +1.50% (50%), Guard at +0.60% (raises SL to -0.10%), 2-hour breakeven at +0.30%
                    has_mid_guard = False
                    sl_level = -0.013
                    realized_pnl = 0.0
                    is_closed = False
                    
                    end_idx = min(len(rows), i + 7200)
                    for j in range(i + 1, end_idx):
                        try:
                            cur_p = float(rows[j][1])
                        except:
                            continue
                        
                        pnl = (cur_p - entry_p) / entry_p if direction == 'LONG' else (entry_p - cur_p) / entry_p
                        
                        # 1. TP hit +1.50%
                        if pnl >= 0.015:
                            realized_pnl = 0.015
                            wins += 1
                            is_closed = True
                            break
                            
                        # 2. Mid guard hit +0.60% -> SL to -0.10%
                        if pnl >= 0.006 and not has_mid_guard:
                            has_mid_guard = True
                            sl_level = -0.0010
                            
                        # 3. 2-hour (7200 rows) check: if >= 3600 and pnl >= 0.003 -> SL to +0.0005
                        if (j - i) >= 3600 and pnl >= 0.003:
                            sl_level = 0.0005
                            
                        # 4. SL hit
                        if pnl <= sl_level:
                            realized_pnl = sl_level
                            if sl_level > 0:
                                wins += 1
                            else:
                                losses += 1
                            is_closed = True
                            break
                            
                    if not is_closed:
                        # End of day / data close at current PnL
                        realized_pnl = pnl
                        if realized_pnl > 0: wins += 1
                        else: losses += 1
                        
                    total_pnl += realized_pnl
                    i += 300 # 5 min cooldown
                else:
                    i += 1
                    
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return total_trades, wins, losses, win_rate, total_pnl

t1, w1, l1, wr1, pnl1 = run_strategy(only_pos_oi=False)
t2, w2, l2, wr2, pnl2 = run_strategy(only_pos_oi=True)

print(f"[1안: 전체 (+OI & -OI)]: Trades={t1}, Wins={w1}, Losses={l1}, WinRate={wr1:.2f}%, Total PnL={pnl1*100:+.2f}%")
print(f"[2안: +OI 전용 (Case C & D)]: Trades={t2}, Wins={w2}, Losses={l2}, WinRate={wr2:.2f}%, Total PnL={pnl2*100:+.2f}%")
