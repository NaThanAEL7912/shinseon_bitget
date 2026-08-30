import os, sys, pickle
from datetime import datetime

CACHE_FILE = "scratch/parsed_session_data.pkl"

def get_session_key_and_name(ts):
    dt = datetime.fromtimestamp(ts)
    w = dt.weekday()
    h = dt.hour
    m = dt.minute
    is_wk = (w == 5 and (h > 6 or (h == 6 and m >= 0))) or (w == 6) or (w == 0 and h < 7)
    
    if 9 <= h < 16 or (h == 16 and m < 30):
        return ('weekend_asia' if is_wk else 'asia', '아시아 (주말)' if is_wk else '아시아 (평일)')
    elif (16 <= h < 22 or (h == 22 and m < 30)) and not (h == 16 and m < 30):
        return ('weekend_europe' if is_wk else 'europe', '유럽 (주말)' if is_wk else '유럽 (평일)')
    elif (h == 22 and m >= 30) or h >= 23 or h < 5:
        return ('weekend_us' if is_wk else 'us', '미국 본장 (주말)' if is_wk else '미국 본장 (평일)')
    else:
        return ('weekend_pacific' if is_wk else 'pacific', '태평양 (주말)' if is_wk else '태평양 (평일)')

def run_continuous_simulation(config, start_dt=None, end_dt=None):
    with open(CACHE_FILE, 'rb') as f:
        raw_sdata = pickle.load(f)
        
    start_ts = start_dt.timestamp() if start_dt else 0.0
    end_ts = end_dt.timestamp() if end_dt else 9999999999.0
    
    initial_balance = float(config.get('initial_balance', 10000.0))
    fee_rate = float(config.get('fee_rate', 0.00030))
    
    sessions_cfg = config.get('sessions', {})
    trading_cfg = config.get('trading', {})
    guard_cfg = config.get('guardrails', {})
    tp1_split_ratio = float(guard_cfg.get('tp1_split_ratio', 50.0)) / 100.0
    
    # 8대 세션 정의
    session_keys = [
        ('asia', '아시아 (평일)'),
        ('europe', '유럽 (평일)'),
        ('us', '미국 본장 (평일)'),
        ('pacific', '태평양 (평일)'),
        ('weekend_asia', '아시아 (주말)'),
        ('weekend_europe', '유럽 (주말)'),
        ('weekend_us', '미국 본장 (주말)'),
        ('weekend_pacific', '태평양 (주말)')
    ]
    
    session_summary = {}
    for s_k, s_n in session_keys:
        session_summary[s_k] = {
            'name': s_n, 'trades': 0, 'wins': 0, 'losses': 0,
            'win_rate': 0.0, 'gross': 0.0, 'fee': 0.0, 'net': 0.0, 'roi': 0.0
        }
        
    # 전체 틱 통합 및 시간 정렬
    unified = []
    seen = set()
    for k, rows in raw_sdata.items():
        for r in rows:
            ts = r['ts']
            if ts not in seen and start_ts <= ts <= end_ts:
                seen.add(ts)
                unified.append(r)
    unified.sort(key=lambda x: x['ts'])
    
    all_trade_logs = []
    
    is_in = has_2nd = has_3rd = is_tp1 = False
    direction = None
    ep1 = ep2 = ep3 = ep = peak_pnl = min_pnl = 0.0
    cooldown = last_split_entry_time = last_entry_time = 0.0
    current_trade = {}
    history_window = []
    
    for r in unified:
        cp = r.get('price', 0.0)
        cts = r.get('ts', 0.0)
        if cp <= 1000.0:
            continue
            
        history_window.append((cts, cp))
        while history_window and history_window[0][0] < cts - 5.0:
            history_window.pop(0)
        p_5s_ago = history_window[0][1] if history_window else cp
        price_delta_5s = cp - p_5s_ago
        
        liq_total = r.get('liq', 0.0)
        oi_speed = r.get('oi', 0.0)
        
        s_cfg_key, s_name = get_session_key_and_name(cts)
        s_thresh = sessions_cfg.get(s_cfg_key, {})
        t_liq = float(s_thresh.get('liq', 250000))
        t_oi = float(s_thresh.get('oi', 0.0400))
        sl_pct = float(s_thresh.get('sl', -0.6))
        sl_ratio = abs(sl_pct) / 100.0
        
        t_sess = trading_cfg.get(s_cfg_key, {})
        buy_ratio_1 = float(t_sess.get('buy1_ratio', 300.0)) / 100.0
        buy_ratio_2 = float(t_sess.get('buy2_ratio', 150.0)) / 100.0
        buy_ratio_3 = float(t_sess.get('buy3_ratio', 150.0)) / 100.0
        dca_drop = float(t_sess.get('dca_drop', -0.30)) / 100.0
        dca_drop_3 = float(t_sess.get('dca_drop_3', -0.60)) / 100.0
        dca_time_limit = float(t_sess.get('dca_time_limit', 900.0))
        sl_cooldown = float(t_sess.get('sl_cooldown', 30.0))
        tp_cooldown = float(t_sess.get('tp_cooldown', 10.0))
        
        g_sess = guard_cfg.get(s_cfg_key, {})
        tp1_pct = float(g_sess.get('tp1', 0.40))
        tp2_pct = float(g_sess.get('tp2', 0.80))
        be_guard_pct = float(g_sess.get('be_guard', 0.00))
        tp1_ratio = tp1_pct / 100.0
        tp2_ratio = tp2_pct / 100.0
        be_guard_ratio = be_guard_pct / 100.0
        
        # 4대 헌법 신호 판정
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
                strat_name = "4️⃣ 역V자 천장 덤핑 숏"
                
        if not is_in:
            if cts < cooldown:
                continue
            if not s_thresh.get('enabled', True):
                continue
            if sig_dir in ["LONG", "SHORT"]:
                is_in = True
                has_2nd = False
                has_3rd = False
                ep2 = 0.0
                ep3 = 0.0
                is_tp1 = False
                direction = sig_dir
                ep1 = ep = cp
                peak_pnl = 0.0
                min_pnl = 0.0
                last_split_entry_time = 0.0
                last_entry_time = cts
                
                strat_name = strat_name if strat_name else ("🟢 롱 저격" if direction == "LONG" else "🔴 숏 저격")
                current_trade = {
                    'session': s_name,
                    'session_key': s_cfg_key,
                    'entry_time': datetime.fromtimestamp(cts).strftime('%Y-%m-%d %H:%M:%S'),
                    'entry_ts': cts,
                    'dir': direction,
                    'strategy': strat_name,
                    'entry_price': ep1,
                    'liq': liq_total,
                    'oi': oi_speed,
                    'has_2nd': False,
                    'effective_lev': buy_ratio_1,
                    'buy_ratio_1': buy_ratio_1,
                    'buy_ratio_2': buy_ratio_2,
                    'buy_ratio_3': buy_ratio_3,
                    'dca_drop': dca_drop,
                    'dca_drop_3': dca_drop_3,
                    'dca_time_limit': dca_time_limit,
                    'sl_ratio': sl_ratio,
                    'sl_pct': sl_pct,
                    'sl_cooldown': sl_cooldown,
                    'tp_cooldown': tp_cooldown,
                    'tp1_ratio': tp1_ratio,
                    'tp1_pct': tp1_pct,
                    'tp2_ratio': tp2_ratio,
                    'tp2_pct': tp2_pct,
                    'be_guard_ratio': be_guard_ratio,
                    'be_guard_pct': be_guard_pct
                }
        else:
            # 포지션 보유 중
            pnl1 = (cp - ep1) / ep1 if direction == "LONG" else (ep1 - cp) / ep1
            pnl_cur = (cp - ep) / ep if direction == "LONG" else (ep - cp) / ep
            peak_pnl = max(peak_pnl, pnl_cur)
            min_pnl = min(min_pnl, pnl_cur)
            
            t_buy1 = current_trade['buy_ratio_1']
            t_buy2 = current_trade['buy_ratio_2']
            t_buy3 = current_trade['buy_ratio_3']
            t_dca_drop = current_trade['dca_drop']
            t_dca_drop_3 = current_trade['dca_drop_3']
            t_dca_limit = current_trade['dca_time_limit']
            t_sl_ratio = current_trade['sl_ratio']
            t_sl_pct = current_trade['sl_pct']
            t_sl_cd = current_trade['sl_cooldown']
            t_tp_cd = current_trade['tp_cooldown']
            t_tp1_ratio = current_trade['tp1_ratio']
            t_tp1_pct = current_trade['tp1_pct']
            t_tp2_ratio = current_trade['tp2_ratio']
            t_tp2_pct = current_trade['tp2_pct']
            t_be_guard_ratio = current_trade['be_guard_ratio']
            t_be_guard_pct = current_trade['be_guard_pct']
            
            # 2차 추매
            if not has_2nd and t_buy2 > 0.0:
                if pnl1 <= t_dca_drop and sig_dir == direction and (cts - last_split_entry_time >= t_dca_limit):
                    has_2nd = True
                    ep2 = cp
                    ep = (ep1 * t_buy1 + ep2 * t_buy2) / (t_buy1 + t_buy2)
                    last_split_entry_time = cts
                    current_trade['has_2nd'] = True
                    current_trade['effective_lev'] = t_buy1 + t_buy2
                    
            # 3차 추매
            if has_2nd and not has_3rd and t_buy3 > 0.0:
                if pnl1 <= t_dca_drop_3 and sig_dir == direction and (cts - last_split_entry_time >= t_dca_limit):
                    has_3rd = True
                    ep3 = cp
                    ep = (ep1 * t_buy1 + ep2 * t_buy2 + ep3 * t_buy3) / (t_buy1 + t_buy2 + t_buy3)
                    last_split_entry_time = cts
                    current_trade['has_3rd'] = True
                    current_trade['effective_lev'] = t_buy1 + t_buy2 + t_buy3
                    
            closed = False
            fp = 0.0
            cd = t_tp_cd
            reason = ""
            
            # 1차 익절
            if not is_tp1 and pnl_cur >= t_tp1_ratio:
                is_tp1 = True
                
            # 불타기
            if is_tp1 and not getattr(current_trade, 'has_pyramided', False) and pnl_cur <= (t_tp1_ratio - 0.003):
                current_trade['has_pyramided'] = True
                current_trade['orig_lev'] = current_trade['effective_lev']
                rem_lev = current_trade['orig_lev'] * (1.0 - tp1_split_ratio)
                pyra_lev = 30.0
                new_lev = rem_lev + pyra_lev
                ep = (rem_lev * ep + pyra_lev * cp) / new_lev
                current_trade['effective_lev'] = new_lev
                current_trade['be_guard_ratio'] = 0.0
                
            # 가드레일 (시간 & 중간보존)
            if not getattr(current_trade, 'has_time_guard', False) and (cts - last_entry_time >= 7200.0) and pnl_cur >= 0.003:
                current_trade['has_time_guard'] = True
                current_trade['time_guard_pnl'] = 0.0005
                
            if not getattr(current_trade, 'has_mid_guard', False) and pnl_cur >= 0.006:
                current_trade['has_mid_guard'] = True
                current_trade['mid_guard_pnl'] = -0.0010
                
            # 청산 분기
            if is_tp1 and pnl_cur >= t_tp2_ratio:
                closed = True
                fp = t_tp2_ratio * (1.0 - tp1_split_ratio)
                cd = t_tp_cd
                reason = f"2차올킬 (+{t_tp2_pct:.2f}%)"
            elif is_tp1 and pnl_cur <= t_be_guard_ratio:
                closed = True
                fp = t_be_guard_ratio * (1.0 - tp1_split_ratio)
                cd = t_tp_cd
                reason = f"본전가드 (+{t_be_guard_pct:.2f}%)"
            elif not is_tp1 and getattr(current_trade, 'has_mid_guard', False) and pnl_cur <= current_trade['mid_guard_pnl']:
                closed = True
                fp = current_trade['mid_guard_pnl']
                cd = t_tp_cd if fp > 0 else t_sl_cd
                reason = "중간 수익 보존 가드 (-0.1%)"
            elif not is_tp1 and getattr(current_trade, 'has_time_guard', False) and pnl_cur <= current_trade['time_guard_pnl']:
                closed = True
                fp = current_trade['time_guard_pnl']
                cd = t_tp_cd
                reason = "2시간 무위험 본전 탈출 (+0.05%)"
            elif not is_tp1 and pnl1 <= -t_sl_ratio:
                closed = True
                exit_p = ep1 * (1.0 - t_sl_ratio) if direction == "LONG" else ep1 * (1.0 + t_sl_ratio)
                fp = (exit_p - ep) / ep if direction == "LONG" else (ep - exit_p) / ep
                cd = t_sl_cd
                reason = f"손절 (-{abs(t_sl_pct):.2f}%)"
            elif (cts - last_entry_time >= 60.0) and sig_dir and (sig_dir != direction):
                closed = True
                rem = (1.0 - tp1_split_ratio) if is_tp1 else 1.0
                fp = pnl_cur * rem
                cd = t_tp_cd if pnl_cur > 0 else t_sl_cd
                reason = f"반대신호 ({sig_dir})"
                
            if closed:
                tp1_profit = 0.0
                tp1_notional = 0.0
                if is_tp1:
                    orig_lev = current_trade.get('orig_lev', current_trade['effective_lev'])
                    tp1_profit = initial_balance * (t_tp1_ratio * tp1_split_ratio) * orig_lev
                    tp1_notional = (initial_balance * orig_lev * tp1_split_ratio) * 2.0
                    
                is_pyra = current_trade.get('has_pyramided', False)
                act_lev = current_trade['effective_lev']
                
                if is_pyra:
                    actual_pnl = fp / (1.0 - tp1_split_ratio)
                    rem_profit = initial_balance * actual_pnl * act_lev
                    rem_notional = (initial_balance * act_lev) * (2.0 + actual_pnl)
                else:
                    rem_profit = initial_balance * fp * act_lev
                    actual_pnl = fp / (1.0 - tp1_split_ratio) if is_tp1 else fp
                    rem_notional = (initial_balance * act_lev * ((1.0 - tp1_split_ratio) if is_tp1 else 1.0)) * (2.0 + actual_pnl)
                    
                gross_profit = tp1_profit + rem_profit
                total_notional = tp1_notional + rem_notional
                trade_fee = total_notional * fee_rate
                net_profit = gross_profit - trade_fee
                
                is_win = (gross_profit > 0 or is_tp1)
                
                current_trade['exit_time'] = datetime.fromtimestamp(cts).strftime('%Y-%m-%d %H:%M:%S')
                current_trade['exit_price'] = cp
                current_trade['peak_pnl_pct'] = peak_pnl * 100.0
                current_trade['min_pnl_pct'] = min_pnl * 100.0
                current_trade['gross'] = gross_profit
                current_trade['fee'] = trade_fee
                current_trade['net'] = net_profit
                current_trade['reason'] = reason
                current_trade['is_win'] = is_win
                
                all_trade_logs.append(current_trade)
                
                # 세션 요약에 반영
                s_key = current_trade['session_key']
                if s_key in session_summary:
                    session_summary[s_key]['trades'] += 1
                    if is_win: session_summary[s_key]['wins'] += 1
                    else: session_summary[s_key]['losses'] += 1
                    session_summary[s_key]['gross'] += gross_profit
                    session_summary[s_key]['fee'] += trade_fee
                    session_summary[s_key]['net'] += net_profit
                    
                is_in = False
                cooldown = cts + cd
                
    # 전체 통계
    for s_k, s_d in session_summary.items():
        tr = s_d['trades']
        s_d['win_rate'] = (s_d['wins'] / tr * 100.0) if tr > 0 else 0.0
        s_d['roi'] = (s_d['net'] / initial_balance * 100.0) if initial_balance > 0 else 0.0
        
    total_trades = len(all_trade_logs)
    total_wins = sum(1 for t in all_trade_logs if t['is_win'])
    total_losses = total_trades - total_wins
    overall_win_rate = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0
    total_gross = sum(t['gross'] for t in all_trade_logs)
    total_fee = sum(t['fee'] for t in all_trade_logs)
    total_net = sum(t['net'] for t in all_trade_logs)
    
    # MDD
    peak_equity = initial_balance
    current_equity = initial_balance
    max_dd = 0.0
    max_dd_pct = 0.0
    for t in all_trade_logs:
        current_equity += t['net']
        if current_equity > peak_equity: peak_equity = current_equity
        dd = peak_equity - current_equity
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak_equity * 100.0) if peak_equity > 0 else 0.0
            
    print(f"Total Trades: {total_trades} ({total_wins}W {total_losses}L) WR: {overall_win_rate:.1f}%")
    print(f"Gross: + | Fee: - | Net: ")
    
    reasons = {}
    for t in all_trade_logs:
        reasons[t['reason']] = reasons.get(t['reason'], 0) + 1
    print("\n--- EXIT REASONS ---")
    for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {r}: {c}회")

config = {
    'initial_balance': 10000.0,
    'fee_rate': 0.00030,
    'sessions': {
        'asia': {'enabled': True, 'liq': 800000, 'oi': 0.1500, 'sl': -0.6},
        'europe': {'enabled': True, 'liq': 1000000, 'oi': 0.1500, 'sl': -0.8},
        'us': {'enabled': True, 'liq': 800000, 'oi': 0.2400, 'sl': -1.3},
        'pacific': {'enabled': True, 'liq': 500000, 'oi': 0.1200, 'sl': -1.0}
    },
    'trading': {
        'asia': {'leverage': 30.0, 'buy1_ratio': 300.0, 'buy2_ratio': 150.0, 'buy3_ratio': 150.0, 'dca_drop': -0.30, 'dca_drop_3': -0.60, 'dca_time_limit': 900.0, 'sl_cooldown': 30.0, 'tp_cooldown': 10.0},
        'europe': {'leverage': 30.0, 'buy1_ratio': 300.0, 'buy2_ratio': 150.0, 'buy3_ratio': 150.0, 'dca_drop': -0.30, 'dca_drop_3': -0.60, 'dca_time_limit': 900.0, 'sl_cooldown': 30.0, 'tp_cooldown': 10.0},
        'us': {'leverage': 30.0, 'buy1_ratio': 600.0, 'buy2_ratio': 300.0, 'buy3_ratio': 300.0, 'dca_drop': -0.30, 'dca_drop_3': -0.60, 'dca_time_limit': 900.0, 'sl_cooldown': 30.0, 'tp_cooldown': 10.0},
        'pacific': {'leverage': 30.0, 'buy1_ratio': 200.0, 'buy2_ratio': 100.0, 'buy3_ratio': 100.0, 'dca_drop': -0.30, 'dca_drop_3': -0.60, 'dca_time_limit': 900.0, 'sl_cooldown': 30.0, 'tp_cooldown': 10.0}
    },
    'guardrails': {
        'asia': {'tp1': 0.40, 'tp2': 0.80, 'be_guard': 0.0},
        'europe': {'tp1': 0.40, 'tp2': 0.80, 'be_guard': 0.0},
        'us': {'tp1': 0.40, 'tp2': 0.80, 'be_guard': 0.0},
        'pacific': {'tp1': 0.40, 'tp2': 0.80, 'be_guard': 0.0},
        'tp1_split_ratio': 50.0
    }
}

run_continuous_simulation(config)