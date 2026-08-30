import asyncio, ccxt.async_support as ccxt, aiohttp, time, hmac, hashlib, base64, json

with open('/home/ubuntu/server_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

API_KEY = cfg.get('BITGET_API_KEY')
API_SECRET = cfg.get('BITGET_SECRET_KEY')
PASSPHRASE = cfg.get('BITGET_PASSPHRASE')

async def main():
    ex = ccxt.bitget({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'password': PASSPHRASE,
        'options': {'defaultType': 'swap'}
    })
    
    # 1. Fetch positions
    positions = await ex.fetch_positions(['BTC/USDT:USDT'])
    for p in positions:
        if float(p.get('contracts', 0) or 0) > 0:
            print(f"ACTIVE POSITION: {p['side']} {p['contracts']} BTC @ {p['entryPrice']}")

    # 2. Query plan orders via Bitget V2 REST
    url_base = 'https://api.bitget.com'
    path_plan = '/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss'
    ts = str(int(time.time() * 1000))
    msg = ts + 'GET' + path_plan
    mac = hmac.new(API_SECRET.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': API_KEY, 'ACCESS-SIGN': sign, 'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': PASSPHRASE, 'Content-Type': 'application/json'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url_base + path_plan, headers=headers) as resp:
            data = await resp.json()
            print("PLAN ORDERS (profit_loss):")
            print(json.dumps(data, indent=2, ensure_ascii=False))

    await ex.close()

asyncio.run(main())