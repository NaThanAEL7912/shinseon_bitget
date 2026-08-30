# -*- coding: utf-8 -*-
import glob, os, csv

csv_files = sorted(glob.glob('/home/ubuntu/docs/historical_data/orderflow_history_2026-08-1[34567].csv'))

def simulate_strategy(mode="pure"):
    # mode: 'pure' (+OI only for entry & exit)
    # mode: 'hybrid' (+OI for entry, +OI for full exit, but -OI closes 50% if PnL >= +0.40%)
    
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
                    
                # New Entry: ALWAYS +OI only (Case C & D)
                if sig in ['LONG', 'SHORT'] and oi > 0:
                    entry_p = price
                    direction = sig
                    total_trades += 1
                    
                    has_mid_guard = False
                    has_hybrid_50_closed = False
                    sl_level = -0.013
                    realized_pnl = 0.0
                    is_closed = False
                    
                    end_idx = min(len(rows), i + 7200)
                    for j in range(i + 1, end_idx):
                        try:
                            cur_p = float(rows[j][1])
                            cur_oi = float(rows[j][6])
                            cur_sig = rows[j][10].strip()
                        except:
                            continue
                        
                        pnl = (cur_p - entry_p) / entry_p if direction == 'LONG' else (entry_p - cur_p) / entry_p
                        
                        # Check Opposing Signal
                        is_opp_sig = (direction == 'LONG' and cur_sig == 'SHORT') or (direction == 'SHORT' and cur_sig == 'LONG')
                        
                        # 1. Full Exit on +OI opposite signal
                        if is_opp_sig and cur_oi > 0:
                            trade_pnl = pnl
                            if has_hybrid_50_closed:
                                trade_pnl = 0.5 * 0.004 + 0.5 * pnl # 50% locked earlier + 50% remaining
                            realized_pnl = trade_pnl
                            if realized_pnl > 0: wins += 1
                            else: losses += 1
                            is_closed = True
                            break
                            
                        # 2. Hybrid Partial Exit on -OI opposite signal
                        if mode == "hybrid" and is_opp_sig and cur_oi < 0 and not has_hybrid_50_closed:
                            if pnl >= 0.0040: # in profit >= +0.40%
                                has_hybrid_50_closed = True
                                sl_level = 0.0005 # raise remaining 50% to breakeven
                                
                        # 3. TP hit +1.50%
                        if pnl >= 0.015:
                            trade_pnl = 0.015
                            if has_hybrid_50_closed:
                                trade_pnl = 0.5 * 0.004 + 0.5 * 0.015
                            realized_pnl = trade_pnl
                            wins += 1
                            is_closed = True
                            break
                            
                        # 4. Mid guard hit +0.60% -> SL to -0.10%
                        if pnl >= 0.006 and not has_mid_guard:
                            has_mid_guard = True
                            sl_level = max(sl_level, -0.0010)
                            
                        # 5. 2-hour check: if >= 3600 and pnl >= 0.003 -> SL to +0.0005
                        if (j - i) >= 3600 and pnl >= 0.003:
                            sl_level = max(sl_level, 0.0005)
                            
                        # 6. SL hit
                        if pnl <= sl_level:
                            trade_pnl = sl_level
                            if has_hybrid_50_closed:
                                trade_pnl = 0.5 * 0.004 + 0.5 * sl_level
                            realized_pnl = trade_pnl
                            if realized_pnl > 0: wins += 1
                            else: losses += 1
                            is_closed = True
                            break
                            
                    if not is_closed:
                        trade_pnl = pnl
                        if has_hybrid_50_closed:
                            trade_pnl = 0.5 * 0.004 + 0.5 * pnl
                        realized_pnl = trade_pnl
                        if realized_pnl > 0: wins += 1
                        else: losses += 1
                        
                    total_pnl += realized_pnl
                    i += 300
                else:
                    i += 1
                    
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return total_trades, wins, losses, win_rate, total_pnl

t_pure, w_pure, l_pure, wr_pure, pnl_pure = simulate_strategy("pure")
t_hyb, w_hyb, l_hyb, wr_hyb, pnl_hyb = simulate_strategy("hybrid")

print(f"[순수 +OI 전용 (Pure +OI)]: Trades={t_pure}, Wins={w_pure}, Losses={l_pure}, WinRate={wr_pure:.2f}%, Total PnL={pnl_pure*100:+.2f}%")
print(f"[하이브리드 (Hybrid -OI 50% 익절)]: Trades={t_hyb}, Wins={w_hyb}, Losses={l_hyb}, WinRate={wr_hyb:.2f}%, Total PnL={pnl_hyb*100:+.2f}%")
