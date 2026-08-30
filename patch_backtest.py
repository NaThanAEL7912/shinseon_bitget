import sys, re

with open('backtest_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update DCA settings to include 3rd entry
old_dca_settings = '''        buy_ratio_2 = float(t_session_cfg.get('buy2_ratio', 1500.0)) / 100.0   # 15배 2차추매
        dca_drop = float(t_session_cfg.get('dca_drop', -0.30)) / 100.0       # -0.30%
        dca_time_limit = float(t_session_cfg.get('dca_time_limit', 900.0))    # 900초'''

new_dca_settings = '''        buy_ratio_2 = float(t_session_cfg.get('buy2_ratio', 1500.0)) / 100.0   # 15배 2차추매
        buy_ratio_3 = float(t_session_cfg.get('buy3_ratio', 1500.0)) / 100.0   # 15배 3차추매
        dca_drop = float(t_session_cfg.get('dca_drop', -0.30)) / 100.0       # 2차 추매 라인 (-0.30%)
        dca_drop_3 = float(t_session_cfg.get('dca_drop_3', -0.60)) / 100.0   # 3차 추매 라인 (-0.60%)
        dca_time_limit = float(t_session_cfg.get('dca_time_limit', 900.0))    # 900초'''
code = code.replace(old_dca_settings, new_dca_settings)

# 2. Add history window logic to track 5s price
old_loop_init = '''        current_trade = {}
        s_trade_logs = []

        for r in filtered_data:'''

new_loop_init = '''        current_trade = {}
        s_trade_logs = []
        history_window = []

        for r in filtered_data:'''
code = code.replace(old_loop_init, new_loop_init)

# 3. Add 5s price delta calculation
old_loop_start = '''            if cp <= 1000.0:  # 결측치 필터링
                continue

            liq_total = r.get('liq', 0.0)'''

new_loop_start = '''            if cp <= 1000.0:  # 결측치 필터링
                continue

            # 5초 전 가격 추적
            history_window.append((cts, cp))
            while history_window and history_window[0][0] < cts - 5.0:
                history_window.pop(0)
            p_5s_ago = history_window[0][1] if history_window else cp
            price_delta_5s = cp - p_5s_ago

            liq_total = r.get('liq', 0.0)'''
code = code.replace(old_loop_start, new_loop_start)

# 4. Update the signal detection logic
old_signal_logic = '''            # 🎯 [신선 실전 챔피언 오더플로우 판정: 청산액 + OI + 추세기울기]
            # -------------------------------------------------------------
            sig_dir = None
            if liq_total >= t_liq and oi_speed > 0 and oi_speed >= t_oi:
                s = r.get('slope', 0.0) if r.get('slope', 0.0) != 0.0 else r.get('d1m', 0.0)
                if s > 0 and short_liq >= long_liq:
                    sig_dir = "LONG"
                elif s < 0 and long_liq >= short_liq:
                    sig_dir = "SHORT"'''

new_signal_logic = '''            # 🎯 [신선 V7.13 실전 완벽 동기화 4대 저격 헌법: 청산액 + OI + 5초 실시간 변동]
            # -------------------------------------------------------------
            sig_dir = None
            strat_name = ""
            if liq_total >= t_liq and abs(oi_speed) >= t_oi:
                if oi_speed > 0 and price_delta_5s > 0:
                    sig_dir = "LONG"
                    strat_name = "1️⃣ 강력한 불장 돌파 롱"
                elif oi_speed > 0 and price_delta_5s < 0:
                    sig_dir = "SHORT"
                    strat_name = "2️⃣ 강력한 폭락 추세 숏"
                elif oi_speed < 0 and price_delta_5s >= 10.0:
                    sig_dir = "LONG"
                    strat_name = "3️⃣ V자 바닥 반등 롱"
                elif oi_speed < 0 and price_delta_5s <= -10.0:
                    sig_dir = "SHORT"
                    strat_name = "4️⃣ 역V자 천장 덤핑 숏"'''
code = code.replace(old_signal_logic, new_signal_logic)

# 5. Fix strat_name in init
code = code.replace('strat_name = "🟢 롱 저격 발주" if direction == "LONG" else "🔴 숏 저격 발주"', 'strat_name = strat_name if strat_name else ("🟢 롱 저격" if direction == "LONG" else "🔴 숏 저격")')
code = code.replace('has_2nd = False', 'has_2nd = False\n                    has_3rd = False\n                    ep2 = 0.0\n                    ep3 = 0.0')

# 6. Add 3rd DCA
old_dca_logic = '''                # 2차 추매 (DCA)
                if not has_2nd and buy_ratio_2 > 0.0:
                    if pnl1 <= dca_drop and sig_dir == direction and (cts - last_entry >= dca_time_limit):
                        has_2nd = True
                        ep2 = cp
                        # 평단가 가중평균: 1차비중 vs 2차비중
                        ep = (ep1 * buy_ratio_1 + ep2 * buy_ratio_2) / (buy_ratio_1 + buy_ratio_2)
                        current_trade['has_2nd'] = True
                        current_trade['effective_lev'] = buy_ratio_1 + buy_ratio_2'''

new_dca_logic = '''                # 2차 추매 (DCA)
                if not has_2nd and buy_ratio_2 > 0.0:
                    if pnl1 <= dca_drop and sig_dir == direction and (cts - last_entry >= dca_time_limit):
                        has_2nd = True
                        ep2 = cp
                        ep = (ep1 * buy_ratio_1 + ep2 * buy_ratio_2) / (buy_ratio_1 + buy_ratio_2)
                        last_entry = cts
                        current_trade['has_2nd'] = True
                        current_trade['effective_lev'] = buy_ratio_1 + buy_ratio_2
                
                # 3차 추매 (DCA)
                if has_2nd and not has_3rd and buy_ratio_3 > 0.0:
                    if pnl1 <= dca_drop_3 and sig_dir == direction and (cts - last_entry >= dca_time_limit):
                        has_3rd = True
                        ep3 = cp
                        ep = (ep1 * buy_ratio_1 + ep2 * buy_ratio_2 + ep3 * buy_ratio_3) / (buy_ratio_1 + buy_ratio_2 + buy_ratio_3)
                        last_entry = cts
                        current_trade['has_3rd'] = True
                        current_trade['effective_lev'] = buy_ratio_1 + buy_ratio_2 + buy_ratio_3'''
code = code.replace(old_dca_logic, new_dca_logic)

with open('backtest_engine.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("PYTHON REWRITE SUCCESS")