import asyncio
import ccxt.async_support as ccxt
import json

async def test():
    try:
        with open('/home/ubuntu/server_config.json', 'r') as f:
            config = json.load(f)
        exchange = ccxt.bitget({
            'apiKey': config['BITGET_API_KEY'],
            'secret': config['BITGET_SECRET_KEY'],
            'password': config['BITGET_PASSPHRASE'],
            'options': {'defaultType': 'swap'}
        })
        bal = await exchange.fetch_balance()
        print("Futures USDT total:", bal.get('USDT', {}).get('total'))
        await exchange.close()
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
