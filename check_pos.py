import asyncio, os, json, ccxt.async_support as ccxt

def get_env():
    env = {}
    if os.path.exists('/home/ubuntu/.env'):
        with open('/home/ubuntu/.env', 'r') as f:
            for l in f:
                if '=' in l and not l.startswith('#'):
                    k, v = l.strip().split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
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
    print('=== ACTIVE POSITIONS ===')
    for p in active:
        print(f"Side: {p['side']} | Contracts: {p['contracts']} | Entry: {p['entryPrice']} | PnL: {p['unrealizedPnl']}")
    
    trades = await ex.fetch_my_trades('BTC/USDT:USDT', limit=5)
    print('\n=== RECENT TRADES ===')
    for t in trades:
        print(f"Time: {t['datetime']} | Side: {t['side']} | Price: {t['price']} | Amount: {t['amount']} | Cost: {t['cost']}")
        
    await ex.close()

asyncio.run(main())