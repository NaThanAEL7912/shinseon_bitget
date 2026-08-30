# -*- coding: utf-8 -*-
import glob, os, csv

csv_files = sorted(glob.glob('/home/ubuntu/docs/historical_data/orderflow_history_2026-08-1[34567].csv'))
print('Analyzing CSV files:', csv_files)

# Header: Timestamp(KST),BTC_Price($),1m_Rolling_Liq($),1m_Long_Liq($),1m_Short_Liq($),Liq_Threshold($),1m_OI_Speed(%),OI_Speed_Threshold(%),1m_Price_Delta($),1m_Price_Slope,Signal,Bot_State

results_pos_oi = {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0}
results_neg_oi = {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0}

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
                liq = float(row[2])
                oi = float(row[6])
                slope = float(row[9])
                sig = row[10].strip()
            except:
                i += 1
                continue
                
            if sig in ['LONG', 'SHORT']:
                is_pos_oi = (oi > 0)
                entry_p = price
                direction = sig
                
                hit_tp = False
                hit_sl = False
                max_pnl = 0.0
                min_pnl = 0.0
                
                end_idx = min(len(rows), i + 7200)
                for j in range(i + 1, end_idx):
                    try:
                        cur_p = float(rows[j][1])
                    except:
                        continue
                    
                    pnl = (cur_p - entry_p) / entry_p if direction == 'LONG' else (entry_p - cur_p) / entry_p
                    if pnl > max_pnl: max_pnl = pnl
                    if pnl < min_pnl: min_pnl = pnl
                    
                    if pnl >= 0.015:
                        hit_tp = True
                        break
                    if pnl <= -0.013:
                        hit_sl = True
                        break
                
                target_dict = results_pos_oi if is_pos_oi else results_neg_oi
                target_dict['trades'] += 1
                if hit_tp or (not hit_sl and max_pnl >= 0.006):
                    target_dict['wins'] += 1
                    target_dict['total_pnl'] += max(0.005, max_pnl)
                else:
                    target_dict['losses'] += 1
                    target_dict['total_pnl'] += min_pnl
                
                i += 300 # 5 min cooldown
            else:
                i += 1

print('=== POSITIVE OI (+OI: Case C & Case D) RESULTS ===')
total_p = results_pos_oi['trades']
win_p = results_pos_oi['wins']
wr_p = (win_p / total_p * 100) if total_p > 0 else 0
print(f'Trades: {total_p}, Wins: {win_p}, Losses: {results_pos_oi["losses"]}, WinRate: {wr_p:.2f}%, Total PnL: {results_pos_oi["total_pnl"]*100:.2f}%')

print('=== NEGATIVE OI (-OI: Case A & Case B) RESULTS ===')
total_n = results_neg_oi['trades']
win_n = results_neg_oi['wins']
wr_n = (win_n / total_n * 100) if total_n > 0 else 0
print(f'Trades: {total_n}, Wins: {win_n}, Losses: {results_neg_oi["losses"]}, WinRate: {wr_n:.2f}%, Total PnL: {results_neg_oi["total_pnl"]*100:.2f}%')
