import asyncio
import json
import ccxt.async_support as ccxt

async def check():
    ex = ccxt.bitget()
    try:
        m = await ex.load_markets()
        btc = m.get('BTC/USDT:USDT', {})
        print("=== BITGET BTCUSDT MARKET LIMITS FACT ===")
        print("limits.amount:", btc.get('limits', {}).get('amount'))
        print("info.minTradeNum:", btc.get('info', {}).get('minTradeNum'))
        print("precision.amount:", btc.get('precision', {}).get('amount'))
    finally:
        await ex.close()

if __name__ == '__main__':
    asyncio.run(check())
