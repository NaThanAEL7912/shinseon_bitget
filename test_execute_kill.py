import asyncio, json, hmac, hashlib, base64, time, aiohttp
import ccxt.async_support as ccxt

async def test_kill():
    with open("server_config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    
    api_key = cfg.get("BITGET_API_KEY")
    secret_key = cfg.get("BITGET_SECRET_KEY")
    passphrase = cfg.get("BITGET_PASSPHRASE")
    
    print("API Key present:", bool(api_key))
    
    exchange = ccxt.bitget({
        'apiKey': api_key,
        'secret': secret_key,
        'password': passphrase,
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })
    
    try:
        positions = await exchange.fetch_positions()
        print(f"Total positions found: {len(positions)}")
        for pos in positions:
            sym = pos.get('symbol', '')
            contracts = float(pos.get('contracts', 0) or pos.get('size', 0) or 0)
            if contracts > 0:
                print(f"Active Position -> Symbol: {sym}, Side: {pos.get('side')}, Contracts: {contracts}, Entry: {pos.get('entryPrice')}")
                if "BTC" not in sym:
                    raw_sym = sym.replace("/USDT:USDT", "USDT").replace("/USDT", "USDT").replace(":", "").replace("/", "")
                    print(f"🚨 Killing Non-BTC: {sym} ({raw_sym})...")
                    # 1. Cancel orders
                    try:
                        await exchange.cancel_all_orders(sym)
                        print(f"✅ Cancelled orders for {sym}")
                    except Exception as ce:
                        print(f"⚠️ Cancel orders err: {ce}")
                    
                    # 2. Flash close
                    url_base = "https://api.bitget.com"
                    path_flash = "/api/v2/mix/order/close-positions"
                    body_flash = json.dumps({"symbol": raw_sym, "productType": "USDT-FUTURES"})
                    timestamp = str(int(time.time() * 1000))
                    message = timestamp + "POST" + path_flash + body_flash
                    mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
                    sign = base64.b64encode(mac.digest()).decode('utf-8')
                    headers = {
                        'ACCESS-KEY': api_key,
                        'ACCESS-SIGN': sign,
                        'ACCESS-TIMESTAMP': timestamp,
                        'ACCESS-PASSPHRASE': passphrase,
                        'Content-Type': 'application/json',
                        'locale': 'en-US'
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url_base + path_flash, headers=headers, data=body_flash) as resp:
                            res = await resp.json()
                            print(f"Flash close response: {res}")
    finally:
        await exchange.close()

asyncio.run(test_kill())