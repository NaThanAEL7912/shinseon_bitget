import sys

with open('backtest_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add 'has_pyramided' logic after 1st TP
target_tp1 = '''                # 1차 익절 도달 검사
                if not is_tp1 and pnl_cur >= tp1_ratio:
                    is_tp1 = True
                    s_tp1_cnt += 1'''

new_pyra = '''                # 1차 익절 도달 검사
                if not is_tp1 and pnl_cur >= tp1_ratio:
                    is_tp1 = True
                    s_tp1_cnt += 1
                
                # 불타기 (Winning Pyramiding)
                if is_tp1 and not getattr(current_trade, 'has_pyramided', False) and pnl_cur <= (tp1_ratio - 0.003):
                    current_trade['has_pyramided'] = True
                    current_trade['orig_lev'] = current_trade['effective_lev'] # 기존 볼륨 백업
                    
                    # 1차 익절(50%) 후 남은 레버리지 + 30.0 추가
                    rem_lev = current_trade['orig_lev'] * (1.0 - tp1_split_ratio)
                    pyra_lev = 30.0
                    new_lev = rem_lev + pyra_lev
                    
                    # 평단가 가중 평균 재계산
                    ep = (rem_lev * ep + pyra_lev * cp) / new_lev
                    current_trade['effective_lev'] = new_lev
                    
                    # 불타기 이후엔 방어 가드레일 0.0% 본전으로 세팅
                    current_trade['be_guard_ratio'] = 0.0
                    
                    # tp2 타겟도 현재가(ep) 기준으로 재계산해야 하나, 단순화를 위해 유지
'''
code = code.replace(target_tp1, new_pyra)

# 2. Fix exit logic to handle orig_lev and variable sizes
old_exit = '''                if closed:
                    s_trades += 1
                    act_lev = current_trade['effective_lev']
                    gross_profit = initial_balance * fp * act_lev
                    if is_tp1:
                        gross_profit += initial_balance * (tp1_ratio * tp1_split_ratio) * act_lev

                    notional_in = initial_balance * act_lev
                    notional_out = notional_in * (1.0 + fp)
                    total_notional = notional_in + notional_out
                    trade_fee = total_notional * fee_rate
                    net_profit = gross_profit - trade_fee'''

new_exit = '''                if closed:
                    s_trades += 1
                    tp1_profit = 0.0
                    tp1_notional = 0.0
                    
                    if is_tp1:
                        orig_lev = current_trade.get('orig_lev', current_trade['effective_lev'])
                        tp1_profit = initial_balance * (tp1_ratio * tp1_split_ratio) * orig_lev
                        tp1_notional = (initial_balance * orig_lev * tp1_split_ratio) * 2.0
                    
                    # fp는 (1 - tp1_split_ratio)가 곱해진 상태. 불타기를 했다면 fp를 그대로 쓰면 안됨.
                    is_pyra = current_trade.get('has_pyramided', False)
                    act_lev = current_trade['effective_lev']
                    
                    if is_pyra:
                        # 불타기 상태라면 fp에서 곱해진 (1 - tp1_split_ratio)를 제거하고 현재 PnL 자체를 사용
                        actual_pnl = fp / (1.0 - tp1_split_ratio)
                        rem_profit = initial_balance * actual_pnl * act_lev
                        rem_notional = (initial_balance * act_lev) * (2.0 + actual_pnl)
                    else:
                        rem_profit = initial_balance * fp * act_lev
                        # fp 자체가 비중이 반영된 값이므로 notional 계산 보정
                        actual_pnl = fp / (1.0 - tp1_split_ratio) if is_tp1 else fp
                        rem_notional = (initial_balance * act_lev * ((1.0 - tp1_split_ratio) if is_tp1 else 1.0)) * (2.0 + actual_pnl)
                        
                    gross_profit = tp1_profit + rem_profit
                    total_notional = tp1_notional + rem_notional
                    trade_fee = total_notional * fee_rate
                    net_profit = gross_profit - trade_fee'''

code = code.replace(old_exit, new_exit)

with open('backtest_engine.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("PYRAMIDING ADDED")