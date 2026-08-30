import asyncio, aiohttp, json

async def main():
    async with aiohttp.ClientSession() as s:
        # Fetch 15m candles
        async with s.get('https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=15m&limit=20') as r:
            res = await r.json()
            candles = res.get('data', [])
            print('--- LAST 5 15M CANDLES ---')
            for c in candles[:5]:
                # ts, o, h, l, c, vol
                print(f'Time: {c[0]} | O: {c[1]} | H: {c[2]} | L: {c[3]} | C: {c[4]} | Vol: {c[5]}')

        # Fetch 1h candles
        async with s.get('https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity=1H&limit=10') as r:
            res = await r.json()
            candles = res.get('data', [])
            print('--- LAST 5 1H CANDLES ---')
            for c in candles[:5]:
                print(f'Time: {c[0]} | O: {c[1]} | H: {c[2]} | L: {c[3]} | C: {c[4]} | Vol: {c[5]}')

asyncio.run(main())