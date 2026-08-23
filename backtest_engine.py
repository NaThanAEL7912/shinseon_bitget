# -*- coding: utf-8 -*-
"""
신선(SHINSEON) 오더플로우 백테스팅 코어 엔진 (Backtest Engine Core) V2.0
- 실전 서버(core_logic.py, 백서 V7.03) 100% 전수 동기화
- [4대 완성형 오더플로우 매트릭스: 추세돌파 롱/숏, V자반등 롱, 역V자덤핑 숏]
- [0.02% 5초 동적 가격 불감대 필터 (Price Delta Shield)]
- [2단계 50% 분할익절 & 무위험 본전/보존가드 & 스탑로스 손절 & 반대신호 탈출]
- [박호두 50% 할인 0.030% 및 커스텀 수수료 체계 완벽 연동]
"""

import os
import sys
import pickle
from datetime import datetime
from collections import deque

CACHE_FILE = "scratch/parsed_session_data.pkl"

def load_all_session_data():
    """캐시된 8대 세션 초단위 데이터 로드"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def run_backtest_simulation(config, start_dt=None, end_dt=None):
    """
    지정된 설정값 및 기간(start_dt ~ end_dt)을 바탕으로 실전 서버 100% 동일 정밀 시뮬레이션 수행
    """
    raw_sdata = load_all_session_data()
    if not raw_sdata:
        return {'error': '초단위 실측 데이터 파일(parsed_session_data.pkl)이 존재하지 않습니다.'}

    start_ts = start_dt.timestamp() if start_dt else 0.0
    end_ts = end_dt.timestamp() if end_dt else 9999999999.0

    # 1. 설정값 파싱
    initial_balance = float(config.get('initial_balance', 7020.14))
    fee_rate = float(config.get('fee_rate', 0.00030))  # 기본 0.030% (0.00030)
    
    sessions_cfg = config.get('sessions', {})
    trading_cfg = config.get('trading', {})
    guard_cfg = config.get('guardrails', {})
    
    # 8대 세션 맵핑 정의
    session_keys = [
        ('weekday_asia', 'asia', '아시아 (평일)'),
        ('weekday_europe', 'europe', '유럽 (평일)'),
        ('weekday_us', 'us', '미국 본장 (평일)'),
        ('weekday_pacific', 'pacific', '태평양 (평일)'),
        ('weekend_asia', 'weekend_asia', '아시아 (주말)'),
        ('weekend_europe', 'weekend_europe', '유럽 (주말)'),
        ('weekend_us', 'weekend_us', '미국 본장 (주말)'),
        ('weekend_pacific', 'weekend_pacific', '태평양 (주말)')
    ]
    
    all_trade_logs = []
    session_summary = {}

    total_account_gross = 0.0
    total_account_fee = 0.0
    total_account_net = 0.0

    for s_data_key, s_cfg_key, s_name in session_keys:
        s_threshold = sessions_cfg.get(s_cfg_key, {})
        if not s_threshold.get('enabled', True):
            continue
            
        data = raw_sdata.get(s_data_key, [])
        if not data:
            continue
            
        # 기간 필터링
        filtered_data = [r for r in data if start_ts <= r['ts'] <= end_ts]
        if not filtered_data:
            continue

        # 파라미터 로드
        t_liq = float(s_threshold.get('liq', 250000))
        t_oi = float(s_threshold.get('oi', 0.0400))
        sl_pct = float(s_threshold.get('sl', -0.6))
        sl_ratio = abs(sl_pct) / 100.0

        # 트레이딩 핵심 설정 (세션별)
        t_session_cfg = trading_cfg.get(s_cfg_key, {})
        lev_base = float(t_session_cfg.get('leverage', 30))
        buy_ratio_1 = float(t_session_cfg.get('buy1_ratio', 300.0)) / 100.0   # 예: 300% -> 3.0배
        buy_ratio_2 = float(t_session_cfg.get('buy2_ratio', 150.0)) / 100.0   # 예: 150% -> 1.5배
        dca_drop = float(t_session_cfg.get('dca_drop', -0.30)) / 100.0       # -0.30%
        dca_time_limit = float(t_session_cfg.get('dca_time_limit', 900.0))    # 900초
        sl_cooldown = float(t_session_cfg.get('sl_cooldown', 30.0))
        tp_cooldown = float(t_session_cfg.get('tp_cooldown', 10.0))

        # 가드레일 설정
        g_session_cfg = guard_cfg.get(s_cfg_key, {})
        tp1_pct = float(g_session_cfg.get('tp1', 0.80))
        tp2_pct = float(g_session_cfg.get('tp2', 1.20))
        be_guard_pct = float(g_session_cfg.get('be_guard', 0.50))
        
        tp1_ratio = tp1_pct / 100.0
        tp2_ratio = tp2_pct / 100.0
        be_guard_ratio = be_guard_pct / 100.0
        
        tp1_split_ratio = float(guard_cfg.get('tp1_split_ratio', 50.0)) / 100.0  # 50%
        
        # 세션별 시뮬레이션 상태 변수
        is_in = has_2nd = is_tp1 = False
        direction = None
        ep1 = ep2 = ep = peak_pnl = min_pnl = 0.0
        s_trades = s_tp1_cnt = s_tp2_cnt = s_wins = s_losses = 0
        cooldown = last_entry = last_entry_time = 0.0
        
        current_trade = {}
        s_trade_logs = []

        # 5초 동적 가격 불감대 계산용 윈도우 (최근 5초간의 가격 저장)
        price_history_5s = deque()  # (ts, price)

        for r in filtered_data:
            cp = r['price']
            cts = r['ts']
            if cp <= 1000.0:
                continue

            price_history_5s.append((cts, cp))
            while price_history_5s and (cts - price_history_5s[0][0] > 5.5):
                price_history_5s.popleft()

            # 5초 전 가격 대비 변동폭 계산 (delta_5s)
            p_5s_ago = price_history_5s[0][1] if price_history_5s else cp
            delta_5s = (cp - p_5s_ago) / p_5s_ago if p_5s_ago > 0 else 0.0

            # -------------------------------------------------------------
            # 🎯 [신선 실전 서버 100% 동일 4대 오더플로우 매트릭스 판정]
            # -------------------------------------------------------------
            sig_dir = None
            sig_strategy_name = None

            liq_total = r.get('liq', 0.0)
            short_liq = r.get('short_liq', 0.0)
            long_liq = r.get('long_liq', 0.0)
            oi_speed = r.get('oi', 0.0)
            slope = r.get('slope', 0.0) if r.get('slope', 0.0) != 0.0 else r.get('d1m', 0.0)

            # 3대 필수 하드 게이트: 청산액 >= target_liq AND abs(OI) >= target_oi AND abs(delta_5s) >= 0.02%
            if liq_total >= t_liq and abs(oi_speed) >= t_oi and abs(delta_5s) >= 0.00020:
                # 1️⃣ 추세 돌파 롱 (+OI & 숏청산 폭발 & 5초상승 & 기울기상승)
                if oi_speed > 0 and short_liq >= long_liq and delta_5s >= 0.00020 and slope >= 0:
                    sig_dir = "LONG"
                    sig_strategy_name = "1️⃣ 추세돌파 롱"
                # 2️⃣ 추세 돌파 숏 (+OI & 롱청산 폭발 & 5초하락 & 기울기하락)
                elif oi_speed > 0 and long_liq >= short_liq and delta_5s <= -0.00020 and slope <= 0:
                    sig_dir = "SHORT"
                    sig_strategy_name = "2️⃣ 추세돌파 숏"
                # 3️⃣ V자 바닥 반등 롱 (-OI & 롱개미 털림 & 5초 반등턴) 🏹
                elif oi_speed < 0 and long_liq >= short_liq and delta_5s >= 0.00020:
                    sig_dir = "LONG"
                    sig_strategy_name = "3️⃣ V자반등 롱 🏹"
                # 4️⃣ 역V자 천장 덤핑 숏 (-OI & 매수 고갈 & 5초 덤핑턴) 🏹
                elif oi_speed < 0 and short_liq >= long_liq and delta_5s <= -0.00020:
                    sig_dir = "SHORT"
                    sig_strategy_name = "4️⃣ 역V자덤핑 숏 🏹"

            # -------------------------------------------------------------
            # 포지션 진입 및 관리 루프
            # -------------------------------------------------------------
            if not is_in:
                if cts < cooldown:
                    continue
                if sig_dir in ["LONG", "SHORT"]:
                    is_in = True
                    has_2nd = False
                    is_tp1 = False
                    direction = sig_dir
                    ep1 = ep = cp
                    peak_pnl = 0.0
                    min_pnl = 0.0
                    last_entry = cts
                    last_entry_time = cts
                    current_trade = {
                        'session': s_name,
                        'session_key': s_cfg_key,
                        'entry_time': datetime.fromtimestamp(cts).strftime('%Y-%m-%d %H:%M:%S'),
                        'entry_ts': cts,
                        'dir': direction,
                        'strategy': sig_strategy_name,
                        'entry_price': ep1,
                        'liq': liq_total,
                        'oi': oi_speed,
                        'delta_5s_pct': delta_5s * 100.0,
                        'has_2nd': False,
                        'effective_lev': buy_ratio_1
                    }
            else:
                pnl1 = (cp - ep1) / ep1 if direction == "LONG" else (ep1 - cp) / ep1
                pnl_cur = (cp - ep) / ep if direction == "LONG" else (ep - cp) / ep
                peak_pnl = max(peak_pnl, pnl_cur)
                min_pnl = min(min_pnl, pnl_cur)

                # 2차 추매 (DCA)
                if not has_2nd and buy_ratio_2 > 0.0:
                    if pnl1 <= dca_drop and sig_dir == direction and (cts - last_entry >= dca_time_limit):
                        has_2nd = True
                        ep2 = cp
                        # 평단가 가중평균: 1차비중 vs 2차비중
                        ep = (ep1 * buy_ratio_1 + ep2 * buy_ratio_2) / (buy_ratio_1 + buy_ratio_2)
                        current_trade['has_2nd'] = True
                        current_trade['effective_lev'] = buy_ratio_1 + buy_ratio_2

                closed = False
                fp = 0.0
                cd = tp_cooldown
                reason = ""

                # 1차 익절 도달 검사
                if not is_tp1 and pnl_cur >= tp1_ratio:
                    is_tp1 = True
                    s_tp1_cnt += 1

                # 4단계 청산 조건 분기
                if is_tp1 and pnl_cur >= tp2_ratio:
                    closed = True
                    fp = tp2_ratio * (1.0 - tp1_split_ratio)
                    cd = tp_cooldown
                    s_tp2_cnt += 1
                    reason = f"2차올킬 (+{tp2_pct:.2f}%)"
                elif is_tp1 and pnl_cur <= be_guard_ratio:
                    closed = True
                    fp = be_guard_ratio * (1.0 - tp1_split_ratio)
                    cd = tp_cooldown
                    reason = f"본전/보존가드 (+{be_guard_pct:.2f}%)"
                elif not is_tp1 and pnl_cur <= -sl_ratio:
                    closed = True
                    fp = -sl_ratio
                    cd = sl_cooldown
                    reason = f"스탑로스 손절 ({sl_pct:.2f}%)"
                elif (cts - last_entry_time >= 60.0) and sig_dir and (sig_dir != direction):
                    closed = True
                    rem = (1.0 - tp1_split_ratio) if is_tp1 else 1.0
                    fp = pnl_cur * rem
                    cd = tp_cooldown if pnl_cur > 0 else sl_cooldown
                    reason = f"반대신호 전환 ({sig_strategy_name})"

                if closed:
                    s_trades += 1
                    act_lev = current_trade['effective_lev']
                    gross_profit = initial_balance * fp * act_lev
                    if is_tp1:
                        gross_profit += initial_balance * (tp1_ratio * tp1_split_ratio) * act_lev

                    notional_in = initial_balance * act_lev
                    notional_out = notional_in * (1.0 + fp)
                    total_notional = notional_in + notional_out
                    trade_fee = total_notional * fee_rate
                    net_profit = gross_profit - trade_fee

                    is_win = (gross_profit > 0 or is_tp1)
                    if is_win:
                        s_wins += 1
                    else:
                        s_losses += 1

                    current_trade['exit_time'] = datetime.fromtimestamp(cts).strftime('%Y-%m-%d %H:%M:%S')
                    current_trade['exit_price'] = cp
                    current_trade['peak_pnl_pct'] = peak_pnl * 100.0
                    current_trade['min_pnl_pct'] = min_pnl * 100.0
                    current_trade['gross'] = gross_profit
                    current_trade['fee'] = trade_fee
                    current_trade['net'] = net_profit
                    current_trade['reason'] = reason
                    current_trade['is_win'] = is_win

                    s_trade_logs.append(current_trade)
                    all_trade_logs.append(current_trade)
                    is_in = False
                    cooldown = cts + cd

        # 세션 마감 시 잔여 포지션 정리
        if is_in:
            s_trades += 1
            act_lev = current_trade['effective_lev']
            fp = pnl_cur * ((1.0 - tp1_split_ratio) if is_tp1 else 1.0)
            gross_profit = initial_balance * fp * act_lev
            if is_tp1:
                gross_profit += initial_balance * (tp1_ratio * tp1_split_ratio) * act_lev
            notional_in = initial_balance * act_lev
            notional_out = notional_in * (1.0 + fp)
            total_notional = notional_in + notional_out
            trade_fee = total_notional * fee_rate
            net_profit = gross_profit - trade_fee
            is_win = (gross_profit > 0 or is_tp1)
            if is_win:
                s_wins += 1
            else:
                s_losses += 1
            current_trade['exit_time'] = datetime.fromtimestamp(cts).strftime('%Y-%m-%d %H:%M:%S')
            current_trade['exit_price'] = cp
            current_trade['peak_pnl_pct'] = peak_pnl * 100.0
            current_trade['min_pnl_pct'] = min_pnl * 100.0
            current_trade['gross'] = gross_profit
            current_trade['fee'] = trade_fee
            current_trade['net'] = net_profit
            current_trade['reason'] = "세션 종료 청산"
            current_trade['is_win'] = is_win
            s_trade_logs.append(current_trade)
            all_trade_logs.append(current_trade)

        s_gross = sum(t['gross'] for t in s_trade_logs)
        s_fee = sum(t['fee'] for t in s_trade_logs)
        s_net = sum(t['net'] for t in s_trade_logs)
        s_wr = (s_wins / s_trades * 100.0) if s_trades > 0 else 0.0

        session_summary[s_cfg_key] = {
            'name': s_name,
            'trades': s_trades,
            'wins': s_wins,
            'losses': s_losses,
            'win_rate': s_wr,
            'gross': s_gross,
            'fee': s_fee,
            'net': s_net,
            'roi': (s_net / initial_balance) * 100.0 if initial_balance > 0 else 0.0
        }

        total_account_gross += s_gross
        total_account_fee += s_fee
        total_account_net += s_net

    # 전체 통계 집계
    all_trade_logs.sort(key=lambda x: x.get('entry_ts', 0.0))
    total_trades = len(all_trade_logs)
    total_wins = sum(1 for t in all_trade_logs if t['is_win'])
    total_losses = total_trades - total_wins
    overall_win_rate = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0

    # MDD (최대 낙폭) 계산
    peak_equity = initial_balance
    current_equity = initial_balance
    max_drawdown_usdt = 0.0
    max_drawdown_pct = 0.0

    for t in all_trade_logs:
        current_equity += t['net']
        if current_equity > peak_equity:
            peak_equity = current_equity
        dd = peak_equity - current_equity
        if dd > max_drawdown_usdt:
            max_drawdown_usdt = dd
            max_drawdown_pct = (dd / peak_equity * 100.0) if peak_equity > 0 else 0.0

    win_nets = [t['net'] for t in all_trade_logs if t['net'] > 0]
    loss_nets = [abs(t['net']) for t in all_trade_logs if t['net'] < 0]
    total_win_amt = sum(win_nets)
    total_loss_amt = sum(loss_nets)
    profit_factor = (total_win_amt / total_loss_amt) if total_loss_amt > 0 else 999.99

    return {
        'initial_balance': initial_balance,
        'final_balance': initial_balance + total_account_net,
        'total_trades': total_trades,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'win_rate': overall_win_rate,
        'total_gross': total_account_gross,
        'total_fee': total_account_fee,
        'total_net': total_account_net,
        'roi': (total_account_net / initial_balance * 100.0) if initial_balance > 0 else 0.0,
        'mdd_usdt': max_drawdown_usdt,
        'mdd_pct': max_drawdown_pct,
        'profit_factor': profit_factor,
        'session_summary': session_summary,
        'trade_logs': all_trade_logs
    }
