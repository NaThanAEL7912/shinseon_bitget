import asyncio, os, json, ccxt.async_support as ccxt

def get_env():
    env = {}
    if os.path.exists('/home/ubuntu/.env'):
        with open('/home/ubuntu/.env', 'r') as f:
            for l in f:
                if '=' in l and not l.startswith('#'):
                    k, v = l.strip().split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get('BITGET_API_KEY') and os.path.exists('/home/ubuntu/server_config.json'):
        with open('/home/ubuntu/server_config.json', 'r') as f:
            cfg = json.load(f)
            env['BITGET_API_KEY'] = cfg.get('BITGET_API_KEY') or cfg.get('api_key')
            env['BITGET_SECRET_KEY'] = cfg.get('BITGET_SECRET_KEY') or cfg.get('secret_key') or cfg.get('secret')
            env['BITGET_PASSPHRASE'] = cfg.get('BITGET_PASSPHRASE') or cfg.get('passphrase')
    return env

async def main():
    env = get_env()
    ex = ccxt.bitget({
        'apiKey': env.get('BITGET_API_KEY'),
        'secret': env.get('BITGET_SECRET_KEY'),
        'password': env.get('BITGET_PASSPHRASE'),
        'options': {'defaultType': 'swap'}
    })
    positions = await ex.fetch_positions(['BTC/USDT:USDT'])
    active = [p for p in positions if float(p.get('contracts', 0) or 0) > 0]
    print('=== [LIVE ACTIVE POSITION] ===')
    for p in active:
        print(f"Side: {p['side'].upper()} | Contracts: {p['contracts']} BTC | EntryPrice: ${p['entryPrice']:,.2f} | UnrealizedPnL: +${p['unrealizedPnl']:,.2f} USDT")
    
    trades = await ex.fetch_my_trades('BTC/USDT:USDT', limit=4)
    print('\n=== [RECENT TRADES] ===')
    for t in trades:
        print(f"Time: {t['datetime']} | Side: {t['side']} | Price: ${t['price']:,.2f} | Amount: {t['amount']} BTC | Cost: ${t['cost']:,.2f}")
        
    await ex.close()

asyncio.run(main())