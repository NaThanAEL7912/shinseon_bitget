from backtest_engine import run_backtest_simulation
import datetime

config = {
    'initial_balance': 10000.0,
    'fee_rate': 0.00030,
    'sessions': {
        'asia': {'enabled': True, 'liq': 250000, 'oi': 0.0400, 'sl': -0.6},
        'us': {'enabled': True, 'liq': 250000, 'oi': 0.0400, 'sl': -0.6}
    },
    'trading': {
        'asia': {'leverage': 30.0, 'buy1_ratio': 3000.0, 'buy2_ratio': 1500.0, 'buy3_ratio': 1500.0, 'dca_drop': -0.30, 'dca_drop_3': -0.60, 'dca_time_limit': 30.0},
        'us': {'leverage': 30.0, 'buy1_ratio': 3000.0, 'buy2_ratio': 1500.0, 'buy3_ratio': 1500.0, 'dca_drop': -0.30, 'dca_drop_3': -0.60, 'dca_time_limit': 30.0}
    },
    'guardrails': {
        'asia': {'tp1': 0.40, 'tp2': 0.80, 'be_guard': 0.0},
        'us': {'tp1': 0.40, 'tp2': 0.80, 'be_guard': 0.0},
        'tp1_split_ratio': 50.0
    }
}

res = run_backtest_simulation(config)
if 'error' in res:
    print(res['error'])
else:
    print(f"Total Trades: {res['total_trades']}")
    print(f"Win Rate: {res['win_rate']:.2f}%")
    print(f"Net ROE (Amt): {res['total_net']:.2f} USDT")