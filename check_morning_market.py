import asyncio, aiohttp, time, hmac, hashlib, base64, json, datetime

with open('/home/ubuntu/server_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

API_KEY = cfg.get('BITGET_API_KEY')
API_SECRET = cfg.get('BITGET_SECRET_KEY')
PASSPHRASE = cfg.get('BITGET_PASSPHRASE')
url_base = 'https://api.bitget.com'

def sign(ts, method, path, qs=''):
    msg = ts + method.upper() + path + ('?' + qs if qs else '')
    h = hmac.new(API_SECRET.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')

async def main():
    async with aiohttp.ClientSession() as s:
        # 1. Ticker
        async with s.get('https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES') as r:
            t_res = await r.json()
            t_data = t_res.get('data', [])
            if isinstance(t_data, list) and len(t_data) > 0:
                t_item = t_data[0]
            elif isinstance(t_data, dict):
                t_item = t_data
            else:
                t_item = {}
            last_p = t_item.get('lastPr')
            high_24h = t_item.get('high24h')
            low_24h = t_item.get('low24h')
            print(f"CURRENT_PRICE: {last_p} | 24H_HIGH: {high_24h} | 24H_LOW: {low_24h}")

        # 2. Recent fills
        ts = str(int(time.time()*1000))
        qs = 'symbol=BTCUSDT&productType=USDT-FUTURES&limit=10'
        sig = sign(ts, 'GET', '/api/v2/mix/order/fills', qs)
        headers = {
            'ACCESS-KEY': API_KEY, 'ACCESS-SIGN': sig, 'ACCESS-TIMESTAMP': ts,
            'ACCESS-PASSPHRASE': PASSPHRASE, 'Content-Type': 'application/json'
        }
        async with s.get(url_base + '/api/v2/mix/order/fills?' + qs, headers=headers) as r:
            res = await r.json()
            print("--- RECENT FILLS ---")
            for fill in res.get('data', {}).get('fillList', []):
                t_str = datetime.datetime.fromtimestamp(int(fill.get('cTime', 0))/1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{t_str}] Side: {fill.get('side')} | Price: {fill.get('price')} | Size: {fill.get('size')} | Profit: {fill.get('profit')} USDT")

        # 3. Orderbook depth
        async with s.get('https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=BTCUSDT&productType=USDT-FUTURES&limit=15') as r:
            ob_res = await r.json()
            ob_data = ob_res.get('data', {})
            print("--- ORDERBOOK TOP 5 ASKS ---")
            for a in ob_data.get('asks', [])[:5]:
                print(f"ASK: {a[0]} | Vol: {a[1]}")
            print("--- ORDERBOOK TOP 5 BIDS ---")
            for b in ob_data.get('bids', [])[:5]:
                print(f"BID: {b[0]} | Vol: {b[1]}")

asyncio.run(main())