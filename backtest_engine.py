# -*- coding: utf-8 -*-
"""
신선(SHINSEON) 오더플로우 24시간 연속 통합 백테스팅 코어 엔진 V7.20
- 기획서 310: 4대 완성형 오더플로우 저격 헌법 (0.04% 동적 불감대 & 1분 EMA 슬로프 & V자 반등) 100% 디지털 트윈 완결
- [오더플로우 4대 저격 헌법: 청산액 + OI속도 + 0.04% 동적 불감대(delta_5s) + 1분 EMA 추세 슬로프]
- [2단계 50% 분할 익절 & 본전가드 & 스탑로스 & 60초 반대신호 탈출 & 쿨타임]
- [2차 즉시 물타기 & 3차 900초 물타기 & 눌림목 30% 불타기 & 중간수익보존/2시간무위험 가드]
"""

import os
import sys
import math
import pickle
import bisect
from datetime import datetime

CACHE_FILE = "scratch/parsed_session_data.pkl"
_CACHED_UNIFIED_TICKS = None
_CACHED_ALL_TS = None

def get_unified_ticks_cached():
    global _CACHED_UNIFIED_TICKS, _CACHED_ALL_TS
    if _CACHED_UNIFIED_TICKS is None:
        raw_sdata = load_all_session_data()
        if not raw_sdata:
            return [], []
        unified_ticks = []
        seen_ts = set()
        for s_k, ticks in raw_sdata.items():
            for r in ticks:
                ts = r.get('ts', 0.0)
                if ts not in seen_ts:
                    seen_ts.add(ts)
                    unified_ticks.append(r)
        unified_ticks.sort(key=lambda x: x['ts'])
        _CACHED_UNIFIED_TICKS = unified_ticks
        _CACHED_ALL_TS = [x['ts'] for x in unified_ticks]
    return _CACHED_UNIFIED_TICKS, _CACHED_ALL_TS

def sync_and_build_all_data(progress_callback=None):
    """
    downloads/ 폴더 및 docs/historical_data/ 폴더 내의 모든 실측 CSV를 전수 스캔하여
    scratch/parsed_session_data.pkl 로 자동 파싱 및 정렬 구축
    """
    import csv
    
    csv_files = []
    # 1. downloads 하위 폴더 스캔
    downloads_dir = "downloads"
    if os.path.exists(downloads_dir):
        for sub in sorted(os.listdir(downloads_dir)):
            sub_p = os.path.join(downloads_dir, sub)
            if os.path.isdir(sub_p):
                for f in sorted(os.listdir(sub_p)):
                    if f.startswith("orderflow_history_") and f.endswith(".csv"):
                        csv_files.append(os.path.join(sub_p, f))
                        
    # 2. docs/historical_data 스캔
    hist_dir = os.path.join("docs", "historical_data")
    if os.path.exists(hist_dir):
        for f in sorted(os.listdir(hist_dir)):
            if f.startswith("orderflow_history_") and f.endswith(".csv"):
                fp = os.path.join(hist_dir, f)
                if fp not in csv_files:
                    csv_files.append(fp)

    # 중복 파일명 제거 (파일명 기준 최신 우선)
    unique_files = {}
    for fp in csv_files:
        fn = os.path.basename(fp)
        unique_files[fn] = fp
    sorted_files = sorted(unique_files.values())

    if not sorted_files:
        return {'success': False, 'error': '파싱할 실측 CSV 파일이 존재하지 않습니다.'}

    # 8대 세션별 버킷
    session_data = {
        'weekday_asia': [],
        'weekday_europe': [],
        'weekday_us': [],
        'weekday_pacific': [],
        'weekend_asia': [],
        'weekend_europe': [],
        'weekend_us': [],
        'weekend_pacific': []
    }
    
    seen_ts = set()
    total_parsed_ticks = 0
    min_ts = 9999999999.0
    max_ts = 0.0

    total_files = len(sorted_files)
    for idx, fp in enumerate(sorted_files):
        if progress_callback:
            progress_callback(int((idx / total_files) * 100), f"{os.path.basename(fp)} 파싱 중...")
        
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    continue
                
                # 컬럼 인덱스 탐색
                ts_idx = 0
                price_idx = 1
                liq_idx = 2
                long_liq_idx = 3
                short_liq_idx = 4
                oi_idx = 6
                
                for row in reader:
                    if len(row) < 3:
                        continue
                    
                    raw_ts = row[ts_idx].replace('="', '').replace('"', '').strip()
                    try:
                        dt = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
                        ts = dt.timestamp()
                    except Exception:
                        continue
                    
                    if ts in seen_ts:
                        continue
                    seen_ts.add(ts)
                    
                    try:
                        price = float(row[price_idx]) if len(row) > price_idx else 0.0
                        if price <= 1000.0:  # 결측치 필터링
                            continue
                        liq = float(row[liq_idx]) if len(row) > liq_idx else 0.0
                        long_liq = float(row[long_liq_idx]) if len(row) > long_liq_idx else 0.0
                        short_liq = float(row[short_liq_idx]) if len(row) > short_liq_idx else 0.0
                        oi = float(row[oi_idx]) if len(row) > oi_idx else 0.0
                    except Exception:
                        continue
                    
                    tick_obj = {
                        'ts': ts,
                        'price': price,
                        'liq': liq,
                        'long_liq': long_liq,
                        'short_liq': short_liq,
                        'oi': oi
                    }
                    
                    # 세션 분류
                    s_key, _ = get_session_key_and_name(ts)
                    map_key = s_key
                    if s_key == 'asia': map_key = 'weekday_asia'
                    elif s_key == 'europe': map_key = 'weekday_europe'
                    elif s_key == 'us': map_key = 'weekday_us'
                    elif s_key == 'pacific': map_key = 'weekday_pacific'
                    
                    if map_key in session_data:
                        session_data[map_key].append(tick_obj)
                        total_parsed_ticks += 1
                        if ts < min_ts: min_ts = ts
                        if ts > max_ts: max_ts = ts
        except Exception as e:
            print(f"Error parsing {fp}: {e}")

    # 각 세션 내 타임스탬프 정렬
    for k in session_data:
        session_data[k].sort(key=lambda x: x['ts'])

    os.makedirs("scratch", exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(session_data, f)

    min_dt = datetime.fromtimestamp(min_ts) if min_ts < 9999999999.0 else datetime.now()
    max_dt = datetime.fromtimestamp(max_ts) if max_ts > 0.0 else datetime.now()

    return {
        'success': True,
        'total_files': total_files,
        'total_ticks': total_parsed_ticks,
        'min_dt': min_dt,
        'max_dt': max_dt
    }

def load_all_session_data():
    """캐시된 8대 세션 초단위 데이터 로드 (없으면 자동 구축)"""
    if not os.path.exists(CACHE_FILE):
        sync_and_build_all_data()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def get_session_key_and_name(ts):
    """타임스탬프(ts)를 바탕으로 현재 KST 세션 키 및 명칭 반환"""
    dt = datetime.fromtimestamp(ts)
    w = dt.weekday()  # 0:월, 1:화, ..., 5:토, 6:일
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

def run_backtest_simulation(config, start_dt=None, end_dt=None):
    """
    24시간 완전 연속 시계열 통합 백테스팅 시뮬레이션 (RAM 캐싱 + 이진 탐색 50배 초고속화 V7.22)
    """
    all_ticks, all_ts = get_unified_ticks_cached()
    if not all_ticks:
        return {'error': '초단위 실측 데이터 파일(parsed_session_data.pkl)이 존재하지 않습니다.'}

    start_ts = start_dt.timestamp() if start_dt else 0.0
    end_ts = end_dt.timestamp() if end_dt else 9999999999.0

    # 1. 초광속 이진 탐색(Bisect) 날짜 슬라이싱 (0.008초)
    idx_start = bisect.bisect_left(all_ts, start_ts)
    idx_end = bisect.bisect_right(all_ts, end_ts)
    unified_ticks = all_ticks[idx_start:idx_end]

    if not unified_ticks:
        return {'error': '선택한 기간 내에 분석 가능한 데이터 틱이 없습니다.'}

    # 2. 설정값 파싱
    initial_balance = float(config.get('initial_balance', 10000.0))
    fee_rate = float(config.get('fee_rate', 0.00030))  # 박호두 50% 할인 (0.030%)
    
    sessions_cfg = config.get('sessions', {})
    trading_cfg = config.get('trading', {})
    guard_cfg = config.get('guardrails', {})
    tp1_split_ratio = float(guard_cfg.get('tp1_split_ratio', 50.0)) / 100.0  # 50%
    pyramiding_enabled = bool(guard_cfg.get('pyramiding_enabled', True))
    pyramiding_ratio = float(guard_cfg.get('pyramiding_ratio', 30.0))
    mid_guard_trigger = float(guard_cfg.get('mid_guard_trigger', 0.60)) / 100.0
    mid_guard_offset = float(guard_cfg.get('mid_guard_offset', 0.20)) / 100.0
    oi_direction_mode = str(config.get('oi_direction_mode', 'POSITIVE_ONLY')).upper()
    
    # 8대 세션 성과 요약 테이블 초기화
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
            'name': s_n,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'gross': 0.0,
            'fee': 0.0,
            'net': 0.0,
            'roi': 0.0
        }

    all_trade_logs = []
    
    # 시뮬레이션 상태 변수
    is_in = has_2nd = has_3rd = is_tp1 = False
    direction = None
    ep1 = ep2 = ep3 = ep = peak_pnl = min_pnl = 0.0
    cooldown = last_split_entry_time = last_entry_time = 0.0
    current_trade = {}
    history_60s = []

    for r in unified_ticks:
        cp = r.get('price', 0.0)
        cts = r.get('ts', 0.0)
        if cp <= 1000.0:  # 결측치 필터링
            continue

        # 60초 가격 슬라이딩 추적창 (5초 전 가격 및 1분 EMA 추세 슬로프 연산)
        history_60s.append((cts, cp))
        while history_60s and cts - history_60s[0][0] > 60.0:
            history_60s.pop(0)

        # 10초 전 및 5초 전 실시간 가격 산출
        price_10s_ago = cp
        price_5s_ago = cp
        for t_samp, p_samp in reversed(history_60s):
            if price_5s_ago == cp and cts - t_samp >= 5.0:
                price_5s_ago = p_samp
            if cts - t_samp >= 10.0:
                price_10s_ago = p_samp
                break
        price_delta_5s = cp - price_5s_ago
        price_delta_10s = cp - price_10s_ago
        dynamic_deadband_5s = max(20.0, cp * 0.0004) if cp > 0 else 30.0

        liq_total = r.get('liq', 0.0)
        short_liq = r.get('short_liq', 0.0)
        long_liq = r.get('long_liq', 0.0)
        oi_speed = r.get('oi', 0.0)

        # 현재 틱의 세션 정보 및 파라미터 로드
        s_cfg_key, s_name = get_session_key_and_name(cts)
        s_thresh = sessions_cfg.get(s_cfg_key, {})
        t_liq = float(s_thresh.get('liq', 250000))
        t_oi = float(s_thresh.get('oi', 0.0400))
        sl_pct = float(s_thresh.get('sl', -0.6))
        sl_ratio = abs(sl_pct) / 100.0

        # 1분 지수가중 선형회귀 추세 기울기 (EMA Slope, 반감기 15.0초) - 필요 시점(임계치 근접/포지션 보유)에만 초고속 연산
        price_slope_1m = 0.0
        if (liq_total >= t_liq * 0.8 and abs(oi_speed) >= t_oi * 0.8) or is_in:
            hl_lambda = 0.04621
            weights = [math.exp(-hl_lambda * (cts - t)) for t, p in history_60s]
            sum_w = sum(weights)
            if sum_w > 0 and len(history_60s) >= 2:
                w_t_bar = sum(w * t for w, (t, p) in zip(weights, history_60s)) / sum_w
                w_p_bar = sum(w * p for w, (t, p) in zip(weights, history_60s)) / sum_w
                cov_tp = sum(w * (t - w_t_bar) * (p - w_p_bar) for w, (t, p) in zip(weights, history_60s)) / sum_w
                var_t = sum(w * ((t - w_t_bar) ** 2) for w, (t, p) in zip(weights, history_60s)) / sum_w
                price_slope_1m = (cov_tp / var_t) if var_t > 0 else 0.0

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
        half_exit_enabled = bool(g_sess.get('enabled', True))
        tp1_ratio = tp1_pct / 100.0
        tp2_ratio = tp2_pct / 100.0
        be_guard_ratio = be_guard_pct / 100.0

        # -------------------------------------------------------------
        # 🎯 [신선 V7.67: 백테스터 엔진 V2.55 황금 4대 매트릭스 100% 실전서버 동기화]
        # -------------------------------------------------------------
        deadband_val = cp * 0.00035  # 0.035% 동적 불감대 (약 $27달러)
        
        is_price_up = (price_delta_5s >= deadband_val) or (price_delta_10s >= deadband_val) or (price_slope_1m >= +0.30)
        is_price_down = (price_delta_5s <= -deadband_val) or (price_delta_10s <= -deadband_val) or (price_slope_1m <= -0.30)
        
        sig_dir = None
        strat_name = ""
        
        # [0단계]: 필수 듀얼 임계치 검사 (청산액 >= t_liq AND |OI속도| >= t_oi)
        if liq_total >= t_liq and abs(oi_speed) >= t_oi:
            # [Case A]: 하락(-OI) ➔ V자 바닥 반등 롱 저격!
            if is_price_down and oi_speed < 0:
                sig_dir = "LONG"
                strat_name = "🟢 롱 저격 (개미 털기 V자 바닥 반등 / -OI)"
                
            # [Case B]: 상승(-OI) ➔ 역V자 천장 덤핑 숏 저격!
            elif is_price_up and oi_speed < 0:
                sig_dir = "SHORT"
                strat_name = "🔴 숏 저격 (숏커버 털기 역V자 천장 덤핑 / -OI)"
                
            # [Case C & D]: +OI (세력의 진짜 양수 자금 유입) ➔ 5초/10초/1분 가격 추세 방향 탑승!
            elif oi_speed > 0:
                if is_price_up:
                    sig_dir = "LONG"
                    strat_name = "🟢 강력한 불장 돌파 롱 (+OI / 상방 추세)"
                elif is_price_down:
                    sig_dir = "SHORT"
                    strat_name = "🔴 강력한 폭락 추세 숏 (+OI / 하방 추세)"
                else:
                    sig_dir = None
            else:
                sig_dir = None
        else:
            sig_dir = None

        # -------------------------------------------------------------
        # 포지션 진입 및 관리 루프
        # -------------------------------------------------------------
        if not is_in:
            if cts < cooldown:
                continue
            if not s_thresh.get('enabled', True):
                continue
            if sig_dir in ["LONG", "SHORT"]:
                is_in = True
                has_2nd = False
                has_3rd = False
                is_tp1 = False
                direction = sig_dir
                ep1 = ep = cp
                ep2 = ep3 = 0.0
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
            # 포지션 보유 중: 진입 시점 세션 파라미터 기반 연속 관리
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

            # 2차 추매 (DCA) - 1차 후 쿨타임 대기 없이 하락+동일신호 시 즉시 발동
            if not has_2nd and t_buy2 > 0.0:
                if pnl1 <= t_dca_drop and sig_dir == direction:
                    has_2nd = True
                    ep2 = cp
                    ep = (ep1 * t_buy1 + ep2 * t_buy2) / (t_buy1 + t_buy2)
                    last_split_entry_time = cts
                    current_trade['has_2nd'] = True
                    current_trade['effective_lev'] = t_buy1 + t_buy2

            # 3차 추매 (DCA) - 2차 후 900초 쿨타임 경과 후 발동
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

            # 1차 익절 도달 검사
            t_half_exit = current_trade.get('half_exit_enabled', True)
            if not is_tp1 and pnl_cur >= t_tp1_ratio:
                is_tp1 = True

            # 눌림목 불타기 (Winning Pyramiding) - pyramiding_enabled 켜져있을 때만
            if is_tp1 and pyramiding_enabled and not current_trade.get('has_pyramided', False) and pnl_cur <= (t_tp1_ratio - 0.003):
                current_trade['has_pyramided'] = True
                current_trade['orig_lev'] = current_trade['effective_lev']
                rem_lev = current_trade['orig_lev'] * ((1.0 - tp1_split_ratio) if t_half_exit else 1.0)
                pyra_lev = pyramiding_ratio
                new_lev = rem_lev + pyra_lev
                ep = (rem_lev * ep + pyra_lev * cp) / new_lev
                current_trade['effective_lev'] = new_lev
                current_trade['be_guard_ratio'] = 0.0

            # 가드레일 (2시간 시간 가드 & 동적 중간 수익 보존 가드)
            if not current_trade.get('has_time_guard', False) and (cts - last_entry_time >= 7200.0) and pnl_cur >= 0.003:
                current_trade['has_time_guard'] = True
                current_trade['time_guard_pnl'] = 0.0005

            # 동적 중간 수익 보존 가드 (UI의 mid_guard_trigger 및 mid_guard_offset 적용)
            if not current_trade.get('has_mid_guard', False) and pnl_cur >= mid_guard_trigger:
                current_trade['has_mid_guard'] = True
                current_trade['mid_guard_pnl'] = mid_guard_offset

            # 4단계 청산 조건 분기
            if is_tp1 and pnl_cur >= t_tp2_ratio:
                closed = True
                fp = t_tp2_ratio * ((1.0 - tp1_split_ratio) if t_half_exit else 1.0)
                cd = t_tp_cd
                reason = f"2차올킬 (+{t_tp2_pct:.2f}%)"
            elif is_tp1 and pnl_cur <= t_be_guard_ratio:
                closed = True
                fp = t_be_guard_ratio * ((1.0 - tp1_split_ratio) if t_half_exit else 1.0)
                cd = t_tp_cd
                reason = f"본전가드 (+{t_be_guard_pct:.2f}%)"
            elif not is_tp1 and current_trade.get('has_mid_guard', False) and pnl_cur <= current_trade['mid_guard_pnl']:
                closed = True
                fp = current_trade['mid_guard_pnl']
                cd = t_tp_cd if fp > 0 else t_sl_cd
                reason = f"중간 수익 보존 가드 (+{mid_guard_offset*100:.2f}%)"
            elif not is_tp1 and current_trade.get('has_time_guard', False) and pnl_cur <= current_trade['time_guard_pnl']:
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

                # 진입 세션 성과 요약 집계
                s_key = current_trade['session_key']
                if s_key in session_summary:
                    session_summary[s_key]['trades'] += 1
                    if is_win:
                        session_summary[s_key]['wins'] += 1
                    else:
                        session_summary[s_key]['losses'] += 1
                    session_summary[s_key]['gross'] += gross_profit
                    session_summary[s_key]['fee'] += trade_fee
                    session_summary[s_key]['net'] += net_profit

                is_in = False
                cooldown = cts + cd

    # 세션별 최종 승률 및 ROI 계산
    for s_k, s_d in session_summary.items():
        tr = s_d['trades']
        s_d['win_rate'] = (s_d['wins'] / tr * 100.0) if tr > 0 else 0.0
        s_d['roi'] = (s_d['net'] / initial_balance * 100.0) if initial_balance > 0 else 0.0

    # 전체 계좌 종합 통계
    total_trades = len(all_trade_logs)
    total_wins = sum(1 for t in all_trade_logs if t['is_win'])
    total_losses = total_trades - total_wins
    overall_win_rate = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0
    total_account_gross = sum(t['gross'] for t in all_trade_logs)
    total_account_fee = sum(t['fee'] for t in all_trade_logs)
    total_account_net = sum(t['net'] for t in all_trade_logs)

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