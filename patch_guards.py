import sys

with open('backtest_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 3. Add mid_guard and time_guard to backtest_engine
old_exit = '''                # 4단계 청산 조건 분기
                if is_tp1 and pnl_cur >= tp2_ratio:
                    closed = True
                    fp = tp2_ratio * (1.0 - tp1_split_ratio)'''

new_exit = '''                # 가드레일 (시간 및 중간 보존)
                if not getattr(current_trade, 'has_time_guard', False) and (cts - last_entry_time >= 7200.0) and pnl_cur >= 0.003:
                    current_trade['has_time_guard'] = True
                    # 120분 경과 시 무위험 본전가드 발동 (+0.05%)
                    current_trade['time_guard_pnl'] = 0.0005
                
                if not getattr(current_trade, 'has_mid_guard', False) and pnl_cur >= 0.006:
                    current_trade['has_mid_guard'] = True
                    # 중간 보존 가드 발동 (-0.10%)
                    current_trade['mid_guard_pnl'] = -0.0010
                
                # 4단계 청산 조건 분기
                if is_tp1 and pnl_cur >= tp2_ratio:
                    closed = True
                    fp = tp2_ratio * (1.0 - tp1_split_ratio)'''
code = code.replace(old_exit, new_exit)

old_sl = '''                elif not is_tp1 and pnl1 <= -sl_ratio:
                    closed = True
                    # 손절은 1차 진입가(pnl1) 기준으로 발동되므로, 평단가(ep) 대비 실제 손실률(fp)을 역산
                    exit_p = ep1 * (1.0 - sl_ratio) if direction == "LONG" else ep1 * (1.0 + sl_ratio)
                    fp = (exit_p - ep) / ep if direction == "LONG" else (ep - exit_p) / ep
                    cd = sl_cooldown
                    reason = f"손절 (-{abs(sl_pct):.2f}%)"'''

new_sl = '''                elif not is_tp1 and getattr(current_trade, 'has_mid_guard', False) and pnl_cur <= current_trade['mid_guard_pnl']:
                    closed = True
                    fp = current_trade['mid_guard_pnl']
                    cd = tp_cooldown if fp > 0 else sl_cooldown
                    reason = "중간 수익 보존 가드 (-0.1%)"
                elif not is_tp1 and getattr(current_trade, 'has_time_guard', False) and pnl_cur <= current_trade['time_guard_pnl']:
                    closed = True
                    fp = current_trade['time_guard_pnl']
                    cd = tp_cooldown
                    reason = "2시간 무위험 본전 탈출 (+0.05%)"
                elif not is_tp1 and pnl1 <= -sl_ratio:
                    closed = True
                    exit_p = ep1 * (1.0 - sl_ratio) if direction == "LONG" else ep1 * (1.0 + sl_ratio)
                    fp = (exit_p - ep) / ep if direction == "LONG" else (ep - exit_p) / ep
                    cd = sl_cooldown
                    reason = f"손절 (-{abs(sl_pct):.2f}%)"'''
code = code.replace(old_sl, new_sl)

with open('backtest_engine.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("GUARDRAILS ADDED")