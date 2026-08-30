import asyncio, json, os, hmac, hashlib, base64, time, aiohttp
import ccxt.async_support as ccxt

async def test_kill():
    cfg = {}
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
                    
    api_key = cfg.get("BITGET_API_KEY")
    secret_key = cfg.get("BITGET_SECRET_KEY")
    passphrase = cfg.get("BITGET_PASSPHRASE")
    
    print(f"API Key present: {bool(api_key)}, Secret present: {bool(secret_key)}")
    
    # Direct REST API Flash Close via aiohttp
    raw_sym = "ETHUSDT"
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
        # 1. Cancel open orders for ETHUSDT
        path_cancel = "/api/v2/mix/order/cancel-all-orders"
        body_cancel = json.dumps({"symbol": raw_sym, "productType": "USDT-FUTURES"})
        t_c = str(int(time.time() * 1000))
        msg_c = t_c + "POST" + path_cancel + body_cancel
        mac_c = hmac.new(secret_key.encode('utf-8'), msg_c.encode('utf-8'), hashlib.sha256)
        sign_c = base64.b64encode(mac_c.digest()).decode('utf-8')
        headers_c = {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sign_c,
            'ACCESS-TIMESTAMP': t_c,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
        async with session.post(url_base + path_cancel, headers=headers_c, data=body_cancel) as resp_c:
            res_c = await resp_c.json()
            print("Cancel Orders Result:", res_c)

        # 2. Flash close
        async with session.post(url_base + path_flash, headers=headers, data=body_flash) as resp:
            res = await resp.json()
            print("Flash Close Result:", res)

asyncio.run(test_kill())