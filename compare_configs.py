import json

with open("shinseon_config.json", "r", encoding="utf-8") as f:
    live_cfg = json.load(f)

with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
    bt_cfg = json.load(f)

print("=== [1. 세션별 임계치 비교 (session_thresholds vs sessions)] ===")
print("세션 | 실전(live) 청산 / OI / SL | 백테스터(bt) 청산 / OI / SL")
print("-" * 75)
for k in ["asia", "europe", "us", "pacific", "weekend_asia", "weekend_europe", "weekend_us", "weekend_pacific"]:
    l_s = live_cfg.get("session_thresholds", {}).get(k, {})
    b_s = bt_cfg.get("sessions", {}).get(k, {})
    l_str = f"Liq: ${l_s.get('liq',0):,.0f} / OI: {l_s.get('oi',0):.2f} / SL: {l_s.get('sl',0):.1f}%"
    b_str = f"Liq: ${b_s.get('liq',0):,.0f} / OI: {b_s.get('oi',0):.2f} / SL: {b_s.get('sl',0):.1f}%"
    print(f"{k:<15} | {l_str:<28} | {b_str}")

print("\n=== [2. 가드레일 비교 (session_guardrails vs guardrails)] ===")
guard_map = {"asia":"ASIA", "europe":"LONDON", "us":"NY", "pacific":"PACIFIC", "weekend_asia":"WEEKEND_ASIA", "weekend_europe":"WEEKEND_LONDON", "weekend_us":"WEEKEND_NY", "weekend_pacific":"WEEKEND_PACIFIC"}
for k, l_k in guard_map.items():
    l_g = live_cfg.get("session_guardrails", {}).get(l_k, {})
    b_g = bt_cfg.get("guardrails", {}).get(k, {})
    l_str = f"TP1: {l_g.get('trigger',0):.2f}% / TP2: {l_g.get('trigger_2',0):.2f}% / BE: {l_g.get('guard',0):.2f}%"
    b_str = f"TP1: {b_g.get('tp1',0):.2f}% / TP2: {b_g.get('tp2',0):.2f}% / BE: {b_g.get('be_guard',0):.2f}%"
    print(f"{k:<15} | {l_str:<28} | {b_str}")

print("\n=== [3. 배팅 비중 비교 (session_trading_configs vs trading)] ===")
for k in ["asia", "europe", "us", "pacific", "weekend_asia", "weekend_europe", "weekend_us", "weekend_pacific"]:
    l_t = live_cfg.get("session_trading_configs", {}).get(k, {})
    b_t = bt_cfg.get("trading", {}).get(k, {})
    l_str = f"1차: {l_t.get('split_entry_1_ratio',0):.0f}% / 2차: {l_t.get('split_entry_2_ratio',0):.0f}% / DCA: {l_t.get('split_entry_2_trigger_pct',0):.2f}%"
    b_str = f"1차: {b_t.get('buy1_ratio',0):.0f}% / 2차: {b_t.get('buy2_ratio',0):.0f}% / DCA: {b_t.get('dca_drop',0):.2f}%"
    print(f"{k:<15} | {l_str:<28} | {b_str}")