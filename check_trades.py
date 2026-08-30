import asyncio, ccxt.async_support as ccxt, json

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

async def check():
    ex = ccxt.bitget({
        'apiKey': cfg['api_key'],
        'secret': cfg['secret'],
        'password': cfg['passphrase'],
        'options': {'defaultType': 'swap'}
    })
    positions = await ex.fetch_positions(['BTC/USDT:USDT'])
    active = [p for p in positions if float(p.get('contracts', 0) or 0) > 0]
    print("=== ACTIVE POSITIONS ===")
    for p in active:
        print(f"Side: {p['side']} | Contracts: {p['contracts']} | Entry: {p['entryPrice']} | PnL: {p['unrealizedPnl']}")
    
    trades = await ex.fetch_my_trades('BTC/USDT:USDT', limit=5)
    print("\n=== RECENT TRADES ===")
    for t in trades:
        print(f"Time: {t['datetime']} | Side: {t['side']} | Price: {t['price']} | Amount: {t['amount']} | Cost: {t['cost']}")
    
    orders = await ex.fetch_open_orders('BTC/USDT:USDT')
    print(f"\n=== OPEN ORDERS ({len(orders)}) ===")
    for o in orders:
        print(f"ID: {o['id']} | Type: {o['type']} | Side: {o['side']} | Price: {o['price']} | Amount: {o['amount']}")
    await ex.close()

asyncio.run(check())