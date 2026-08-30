from backtest_engine import run_backtest_simulation

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

res = run_backtest_simulation(config)
reasons = {}
for t in res.get('trade_logs', []):
    r = t.get('reason', '')
    reasons[r] = reasons.get(r, 0) + 1

print("--- EXIT REASONS ---")
for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
    print(f"{r}: {c}회")