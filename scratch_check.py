import json, os

stats_path = '/home/ubuntu/logs/trade_stats_2026-08-07.json'
if os.path.exists(stats_path):
    with open(stats_path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    print("=== 오늘(8/7) 비트겟 저장 체결 내역 (시각 순) ===")
    trades = d.get('trades_detail', [])
    sorted_trades = sorted(trades, key=lambda x: (x.get('date', ''), x.get('time', '')))
    for t in sorted_trades:
        print(f"[{t.get('date')} {t.get('time')}] 방향:{t.get('side')} | 진입:{t.get('entry_p')} | 청산:{t.get('exit_p')} | PnL:${t.get('pnl')} | ROE:{t.get('roe'):.2f}%")
