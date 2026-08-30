import os, glob, datetime

def parse_kst_time(ts_str):
    ts_str = ts_str.strip('="').strip()
    return datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

def run_simulation():
    # Session Thresholds from King's screenshot
    weekday_cfg = {
        "asia": {"liq": 800000.0, "oi": 0.15, "sl": -0.6, "enabled": True},
        "europe": {"liq": 1000000.0, "oi": 0.15, "sl": -0.8, "enabled": True},
        "us": {"liq": 1500000.0, "oi": 0.18, "sl": -1.3, "enabled": True},
        "pacific": {"liq": 500000.0, "oi": 0.12, "sl": -1.0, "enabled": False}
    }
    weekend_cfg = {
        "weekend_asia": {"liq": 200000.0, "oi": 0.04, "sl": -0.6, "enabled": True},
        "weekend_europe": {"liq": 300000.0, "oi": 0.05, "sl": -0.6, "enabled": True},
        "weekend_us": {"liq": 500000.0, "oi": 0.04, "sl": -0.8, "enabled": True},
        "weekend_pacific": {"liq": 150000.0, "oi": 0.03, "sl": -0.5, "enabled": False}
    }

    files = [
        "downloads/2026-08-21/orderflow_history_2026-08-21_NEW.csv",
        "downloads/2026-08-22/orderflow_history_2026-08-22.csv"
    ]

    all_ticks = []
    for f in files:
        if os.path.exists(f):
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                lines = fp.readlines()
                for l in lines[1:]:
                    parts = l.strip().split(",")
                    if len(parts) >= 11:
                        try:
                            dt = parse_kst_time(parts[0])
                            price = float(parts[1])
                            rolling_liq = float(parts[2]) if parts[2] else 0.0
                            long_liq = float(parts[3]) if parts[3] else 0.0
                            short_liq = float(parts[4]) if parts[4] else 0.0
                            oi_speed = float(parts[6]) if parts[6] else 0.0
                            price_delta = float(parts[8]) if parts[8] else 0.0
                            price_slope = float(parts[9]) if parts[9] else 0.0
                            all_ticks.append((dt, price, rolling_liq, long_liq, short_liq, oi_speed, price_delta, price_slope))
                        except:
                            pass

    print(f"Total ticks loaded: {len(all_ticks)}")
    
    # Sort ticks chronologically
    all_ticks.sort(key=lambda x: x[0])

    trades = []
    current_pos = None # {side, entry_price, entry_time, sl_pct, session}
    
    for dt, price, rolling_liq, long_liq, short_liq, oi_speed, price_delta, price_slope in all_ticks:
        # Determine session
        # Check weekend: Saturday after 09:00 or Friday night US
        # In ShinSeon: Friday KST weekday, Saturday 00:00 to 08:59 is Friday US/Pacific or Weekend?
        # KST weekday: dt.weekday() -> 0=Mon, 4=Fri, 5=Sat, 6=Sun
        is_weekend = (dt.weekday() >= 5) # Sat or Sun
        minute_val = dt.hour * 60 + dt.minute
        
        if 539 <= minute_val < 959:
            s_name = "weekend_asia" if is_weekend else "asia"
            cfg = weekend_cfg[s_name] if is_weekend else weekday_cfg[s_name]
        elif 959 <= minute_val < 1349:
            s_name = "weekend_europe" if is_weekend else "europe"
            cfg = weekend_cfg[s_name] if is_weekend else weekday_cfg[s_name]
        elif minute_val >= 1349 or minute_val < 299:
            s_name = "weekend_us" if is_weekend else "us"
            cfg = weekend_cfg[s_name] if is_weekend else weekday_cfg[s_name]
        else:
            s_name = "weekend_pacific" if is_weekend else "pacific"
            cfg = weekend_cfg[s_name] if is_weekend else weekday_cfg[s_name]
            
        if not cfg["enabled"]:
            # If position active during disabled session, let SL/TP manage or continue
            pass
            
        # Check active position exit
        if current_pos:
            entry_p = current_pos["entry_price"]
            side = current_pos["side"]
            sl_pct = current_pos["sl_pct"] # negative e.g. -0.8
            
            pnl_pct = ((price - entry_p) / entry_p * 100.0) if side == "LONG" else ((entry_p - price) / entry_p * 100.0)
            
            # SL exit condition
            if pnl_pct <= sl_pct:
                current_pos["exit_price"] = price
                current_pos["exit_time"] = dt
                current_pos["pnl_pct"] = pnl_pct
                current_pos["reason"] = f"SL ({sl_pct}%)"
                trades.append(current_pos)
                current_pos = None
                continue
                
            # TP Guardrail exit: e.g. +1.0% TP or Trailing or 반대신호
            # Check opposite signal exit
            # Also ShinSeon standard TP: +1.2% or opposite trigger
            if pnl_pct >= 1.2:
                current_pos["exit_price"] = price
                current_pos["exit_time"] = dt
                current_pos["pnl_pct"] = pnl_pct
                current_pos["reason"] = "TP (+1.2%)"
                trades.append(current_pos)
                current_pos = None
                continue

        # Check new entry if no position
        if not current_pos and cfg["enabled"]:
            target_liq = cfg["liq"]
            target_oi = cfg["oi"]
            
            if rolling_liq >= target_liq and abs(oi_speed) >= target_oi:
                # Direction logic
                if long_liq > short_liq or (long_liq == short_liq and price_delta < 0):
                    signal_dir = "SHORT"
                elif short_liq > long_liq or (long_liq == short_liq and price_delta > 0):
                    signal_dir = "LONG"
                else:
                    signal_dir = "SHORT" if price_slope < 0 else "LONG"
                    
                current_pos = {
                    "side": signal_dir,
                    "entry_price": price,
                    "entry_time": dt,
                    "sl_pct": cfg["sl"],
                    "session": s_name
                }

    print(f"\n=== [SIMULATION RESULTS: 2026-08-21 ~ 2026-08-22] ===")
    print(f"Total Trades: {len(trades)}")
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    total_pnl = sum(t["pnl_pct"] for t in trades)
    
    print(f"Win Rate: {win_rate:.1f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Cumulative PnL: {total_pnl:+.2f}%")
    print("\nDetailed Trade Log:")
    for idx, t in enumerate(trades):
        print(f"{idx+1}. [{t['session'].upper()}] {t['entry_time'].strftime('%m-%d %H:%M:%S')} {t['side']} @ ${t['entry_price']:,.1f} -> {t['exit_time'].strftime('%H:%M:%S')} @ ${t['exit_price']:,.1f} | PnL: {t['pnl_pct']:+.2f}% ({t['reason']})")

run_simulation()