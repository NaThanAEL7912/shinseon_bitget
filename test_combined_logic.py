# -*- coding: utf-8 -*-
import json, math
from datetime import datetime
from backtest_engine import load_all_session_data, get_session_key_and_name

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Run simulation with combined Liquidation Dominance + 5s Delta + 1m Slope
raw_sdata = load_all_session_data()
unified_ticks = []
seen_ts = set()
for s_k, ticks in raw_sdata.items():
    for r in ticks:
        ts = r.get("ts", 0.0)
        if ts not in seen_ts:
            seen_ts.add(ts)
            unified_ticks.append(r)
unified_ticks.sort(key=lambda x: x["ts"])

history_60s = []
sessions_cfg = config.get("sessions", {})
trading_cfg = config.get("trading", {})
guard_cfg = config.get("guardrails", {})

fee_rate = 0.0004
initial_balance = 18000.0
balance = initial_balance
trades = []

is_in = False
current_trade = {}
cooldown = 0.0
last_entry_time = 0.0
last_split_entry_time = 0.0
is_tp1 = False
has_2nd = False
has_3rd = False
direction = None
ep = ep1 = ep2 = ep3 = 0.0
peak_pnl = min_pnl = 0.0

for r in unified_ticks:
    cp = r.get("price", 0.0)
    cts = r.get("ts", 0.0)
    if cp <= 1000.0:
        continue
    history_60s.append((cts, cp))
    while history_60s and cts - history_60s[0][0] > 60.0:
        history_60s.pop(0)

    p_5s_ago = cp
    for t_samp, p_samp in reversed(history_60s):
        if cts - t_samp >= 5.0:
            p_5s_ago = p_samp
            break
    price_delta_5s = cp - p_5s_ago

    hl_lambda = 0.04621
    weights = [math.exp(-hl_lambda * (cts - t)) for t, p in history_60s]
    sum_w = sum(weights)
    if sum_w > 0 and len(history_60s) >= 2:
        w_t_bar = sum(w * t for w, (t, p) in zip(weights, history_60s)) / sum_w
        w_p_bar = sum(w * p for w, (t, p) in zip(weights, history_60s)) / sum_w
        cov_tp = sum(w * (t - w_t_bar) * (p - w_p_bar) for w, (t, p) in zip(weights, history_60s)) / sum_w
        var_t = sum(w * ((t - w_t_bar) ** 2) for w, (t, p) in zip(weights, history_60s)) / sum_w
        price_slope_1m = (cov_tp / var_t) if var_t > 0 else 0.0
    else:
        price_slope_1m = 0.0

    dynamic_deadband_5s = max(20.0, cp * 0.0004) if cp > 0 else 30.0

    liq_total = r.get("liq", 0.0)
    short_liq = r.get("short_liq", 0.0)
    long_liq = r.get("long_liq", 0.0)
    oi_speed = r.get("oi", 0.0)

    s_cfg_key, s_name = get_session_key_and_name(cts)
    s_thresh = sessions_cfg.get(s_cfg_key, {})
    t_liq = float(s_thresh.get("liq", 250000))
    t_oi = float(s_thresh.get("oi", 0.0400))
    sl_pct = float(s_thresh.get("sl", -0.6))
    sl_ratio = abs(sl_pct) / 100.0

    t_sess = trading_cfg.get(s_cfg_key, {})
    buy_ratio_1 = float(t_sess.get("buy1_ratio", 300.0)) / 100.0
    buy_ratio_2 = float(t_sess.get("buy2_ratio", 150.0)) / 100.0
    buy_ratio_3 = float(t_sess.get("buy3_ratio", 150.0)) / 100.0
    dca_drop = float(t_sess.get("dca_drop", -0.30)) / 100.0
    dca_drop_3 = float(t_sess.get("dca_drop_3", -0.60)) / 100.0
    dca_time_limit = float(t_sess.get("dca_time_limit", 900.0))
    sl_cooldown = float(t_sess.get("sl_cooldown", 30.0))
    tp_cooldown = float(t_sess.get("tp_cooldown", 10.0))

    g_sess = guard_cfg.get(s_cfg_key, {})
    tp1_pct = float(g_sess.get("tp1", 0.40))
    tp2_pct = float(g_sess.get("tp2", 0.80))
    be_guard_pct = float(g_sess.get("be_guard", 0.00))
    half_exit_enabled = bool(g_sess.get("enabled", True))
    tp1_ratio = tp1_pct / 100.0
    tp2_ratio = tp2_pct / 100.0
    be_guard_ratio = be_guard_pct / 100.0

    sig_dir = None
    if liq_total >= t_liq and abs(oi_speed) >= t_oi:
        # 청산 주도권 결합 저격 헌법
        if short_liq >= long_liq and price_slope_1m >= -0.05:
            sig_dir = "LONG"
        elif long_liq >= short_liq and price_slope_1m <= 0.05:
            sig_dir = "SHORT"

    if not is_in:
        if cts < cooldown:
            continue
        if not s_thresh.get("enabled", True):
            continue
        if sig_dir in ["LONG", "SHORT"]:
            is_in = True
            direction = sig_dir
            ep1 = ep = cp
            last_entry_time = cts
            current_trade = {
                "session": s_name,
                "session_key": s_cfg_key,
                "dir": direction,
                "entry_price": ep1,
                "effective_lev": buy_ratio_1,
                "buy_ratio_1": buy_ratio_1,
                "buy_ratio_2": buy_ratio_2,
                "buy_ratio_3": buy_ratio_3,
                "dca_drop": dca_drop,
                "dca_drop_3": dca_drop_3,
                "dca_time_limit": dca_time_limit,
                "sl_ratio": sl_ratio,
                "sl_pct": sl_pct,
                "sl_cooldown": sl_cooldown,
                "tp_cooldown": tp_cooldown,
                "tp1_ratio": tp1_ratio,
                "tp1_pct": tp1_pct,
                "tp2_ratio": tp2_pct / 100.0,
                "tp2_pct": tp2_pct,
                "be_guard_ratio": be_guard_ratio,
                "be_guard_pct": be_guard_pct,
                "half_exit_enabled": half_exit_enabled
            }
    else:
        pnl1 = (cp - ep1) / ep1 if direction == "LONG" else (ep1 - cp) / ep1
        pnl_cur = (cp - ep) / ep if direction == "LONG" else (ep - cp) / ep
        peak_pnl = max(peak_pnl, pnl_cur)
        min_pnl = min(min_pnl, pnl_cur)

        t_buy1 = current_trade["buy_ratio_1"]
        t_buy2 = current_trade["buy_ratio_2"]
        t_buy3 = current_trade["buy_ratio_3"]
        t_dca_drop = current_trade["dca_drop"]
        t_dca_drop_3 = current_trade["dca_drop_3"]
        t_dca_limit = current_trade["dca_time_limit"]
        t_sl_ratio = current_trade["sl_ratio"]
        t_sl_pct = current_trade["sl_pct"]
        t_sl_cd = current_trade["sl_cooldown"]
        t_tp_cd = current_trade["tp_cooldown"]
        t_tp1_ratio = current_trade["tp1_ratio"]
        t_tp1_pct = current_trade["tp1_pct"]
        t_tp2_ratio = current_trade["tp2_ratio"]
        t_tp2_pct = current_trade["tp2_pct"]
        t_be_guard_ratio = current_trade["be_guard_ratio"]
        t_be_guard_pct = current_trade["be_guard_pct"]

        if not has_2nd and t_buy2 > 0.0:
            if pnl1 <= t_dca_drop and sig_dir == direction:
                has_2nd = True
                ep2 = cp
                ep = (ep1 * t_buy1 + ep2 * t_buy2) / (t_buy1 + t_buy2)
                last_split_entry_time = cts
                current_trade["effective_lev"] = t_buy1 + t_buy2

        if has_2nd and not has_3rd and t_buy3 > 0.0:
            if pnl1 <= t_dca_drop_3 and sig_dir == direction and (cts - last_split_entry_time >= t_dca_limit):
                has_3rd = True
                ep3 = cp
                ep = (ep1 * t_buy1 + ep2 * t_buy2 + ep3 * t_buy3) / (t_buy1 + t_buy2 + t_buy3)
                last_split_entry_time = cts
                current_trade["effective_lev"] = t_buy1 + t_buy2 + t_buy3

        closed = False
        fp = 0.0
        cd = t_tp_cd
        reason = ""

        t_half_exit = current_trade.get("half_exit_enabled", True)
        if not is_tp1 and pnl_cur >= t_tp1_ratio:
            is_tp1 = True

        if is_tp1 and not current_trade.get("has_pyramided", False) and pnl_cur <= (t_tp1_ratio - 0.003):
            current_trade["has_pyramided"] = True
            current_trade["orig_lev"] = current_trade["effective_lev"]
            rem_lev = current_trade["orig_lev"] * (0.5 if t_half_exit else 1.0)
            pyra_lev = 30.0
            new_lev = rem_lev + pyra_lev
            ep = (rem_lev * ep + pyra_lev * cp) / new_lev
            current_trade["effective_lev"] = new_lev
            current_trade["be_guard_ratio"] = 0.0

        if not current_trade.get("has_time_guard", False) and (cts - last_entry_time >= 7200.0) and pnl_cur >= 0.003:
            current_trade["has_time_guard"] = True
            current_trade["time_guard_pnl"] = 0.0005

        mid_guard_trigger = float(guard_cfg.get("mid_guard_trigger", 0.60)) / 100.0
        mid_guard_offset = float(guard_cfg.get("mid_guard_offset", 0.20)) / 100.0
        if not current_trade.get("has_mid_guard", False) and pnl_cur >= mid_guard_trigger:
            current_trade["has_mid_guard"] = True
            current_trade["mid_guard_pnl"] = mid_guard_offset

        if is_tp1 and pnl_cur >= t_tp2_ratio:
            closed = True
            fp = t_tp2_ratio * (0.5 if t_half_exit else 1.0)
            cd = t_tp_cd
            reason = "2차올킬"
        elif is_tp1 and pnl_cur <= t_be_guard_ratio:
            closed = True
            fp = t_be_guard_ratio * (0.5 if t_half_exit else 1.0)
            cd = t_tp_cd
            reason = "본전가드"
        elif not is_tp1 and current_trade.get("has_mid_guard", False) and pnl_cur <= current_trade["mid_guard_pnl"]:
            closed = True
            fp = current_trade["mid_guard_pnl"]
            cd = t_tp_cd if fp > 0 else t_sl_cd
            reason = "중간수익가드"
        elif not is_tp1 and current_trade.get("has_time_guard", False) and pnl_cur <= current_trade["time_guard_pnl"]:
            closed = True
            fp = current_trade["time_guard_pnl"]
            cd = t_tp_cd if fp > 0 else t_sl_cd
            reason = "2시간무위험가드"
        elif pnl1 <= -t_sl_ratio:
            closed = True
            fp = pnl_cur
            cd = t_sl_cd
            reason = "손절"
        elif (cts - last_entry_time >= 60.0) and sig_dir and (sig_dir != direction):
            closed = True
            fp = pnl_cur
            cd = t_tp_cd if fp > 0 else t_sl_cd
            reason = "반대신호"

        if closed:
            eff_lev = current_trade["effective_lev"]
            gross_pnl = balance * eff_lev * fp
            if is_tp1 and t_half_exit and (reason not in ["2차올킬", "본전가드"]):
                gross_pnl += balance * eff_lev * 0.5 * t_tp1_ratio
            trade_fee = balance * eff_lev * fee_rate * 2.0
            net_pnl = gross_pnl - trade_fee
            balance += net_pnl
            trades.append({"net": net_pnl, "win": net_pnl > 0, "reason": reason})

            is_in = False
            is_tp1 = False
            has_2nd = False
            has_3rd = False
            cooldown = cts + cd

wins = sum(1 for t in trades if t["win"])
total = len(trades)
wr = (wins / total * 100) if total > 0 else 0
net = balance - initial_balance
roi = (net / initial_balance) * 100
print(f"Total: {total}, Wins: {wins} ({wr:.1f}%), Final Balance: ${balance:,.2f}, Net: ${net:,.2f} ({roi:+.2f}%)")