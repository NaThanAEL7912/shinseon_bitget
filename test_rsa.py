import asyncio
import ccxt.async_support as ccxt
import json

async def test_rsa():
    try:
        with open('server_config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        with open('shinseon-key.pem', 'r') as f:
            pem = f.read()

        bitget = ccxt.bitget({
            'apiKey': cfg.get('BITGET_API_KEY', ''),
            'secret': pem,
            'password': cfg.get('BITGET_PASSPHRASE', ''),
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        
        bal = await bitget.fetch_balance()
        print('SUCCESS:', bal.get('USDT', {}).get('total', 0.0))
        await bitget.close()
    except Exception as e:
        print('ERROR:', e)

asyncio.run(test_rsa())
