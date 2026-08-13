import asyncio
import json
from shinseon_server import BotCore

async def inspect():
    bot = BotCore()
    if bot.bitget_exchange:
        trades = await bot.bitget_exchange.fetch_my_trades(symbol='BTC/USDT:USDT', limit=10)
        print(f"=== FETCHED TRADES COUNT: {len(trades)} ===")
        for i, t in enumerate(trades):
            print(f"[{i}] ID: {t.get('id')} | Time: {t.get('datetime')} | Side: {t.get('side')} | Price: {t.get('price')} | Qty: {t.get('amount')}")
            print(f"    INFO: {json.dumps(t.get('info', {}), ensure_ascii=False)}")
        await bot.bitget_exchange.close()
    else:
        print("ERROR: bitget_exchange not initialized")

if __name__ == '__main__':
    asyncio.run(inspect())
