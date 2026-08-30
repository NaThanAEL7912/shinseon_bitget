import aiohttp, asyncio, json, hmac, hashlib, base64, time, os
from datetime import datetime, timezone, timedelta

def get_env():
    env = {}
    if os.path.exists('/home/ubuntu/.env'):
        with open('/home/ubuntu/.env', 'r') as f:
            for l in f:
                if '=' in l and not l.startswith('#'):
                    k, v = l.strip().split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get('BITGET_API_KEY') and os.path.exists('/home/ubuntu/server_config.json'):
        with open('/home/ubuntu/server_config.json', 'r') as f:
            cfg = json.load(f)
            env['BITGET_API_KEY'] = cfg.get('BITGET_API_KEY') or cfg.get('api_key')
            env['BITGET_SECRET_KEY'] = cfg.get('BITGET_SECRET_KEY') or cfg.get('secret_key') or cfg.get('secret')
            env['BITGET_PASSPHRASE'] = cfg.get('BITGET_PASSPHRASE') or cfg.get('passphrase')
    return env

async def get_fills_and_bills():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    
    # 2026-08-20 KST (UTC+9): 2026-08-19 15:00:00 UTC ~ 2026-08-20 15:00:00 UTC
    kst = timezone(timedelta(hours=9))
    start_kst = datetime(2026, 8, 20, 0, 0, 0, tzinfo=kst)
    end_kst = datetime(2026, 8, 20, 23, 59, 59, 999000, tzinfo=kst)
    
    start_ts = int(start_kst.timestamp() * 1000)
    end_ts = int(end_kst.timestamp() * 1000)
    
    print(f"Querying fills for 2026-08-20 KST: {start_kst} ({start_ts}) ~ {end_kst} ({end_ts})")
    
    async with aiohttp.ClientSession() as session:
        # 1. Query Fills (Transaction Fills / Trading Fees)
        path = f"/api/v2/mix/order/fills?symbol=BTCUSDT&productType=USDT-FUTURES&startTime={start_ts}&endTime={end_ts}&limit=100"
        timestamp = str(int(time.time() * 1000))
        message = timestamp + "GET" + path
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
        
        fills = []
        async with session.get(url_base + path, headers=headers) as resp:
            res = await resp.json()
            if res.get('code') == '00000' and res.get('data'):
                fills = res['data'].get('fillList', [])
        
        # Also query bills
        # /api/v2/mix/account/bill
        path_bill = f"/api/v2/mix/account/bill?symbol=BTCUSDT&productType=USDT-FUTURES&coin=USDT&startTime={start_ts}&endTime={end_ts}&limit=100"
        timestamp = str(int(time.time() * 1000))
        message = timestamp + "GET" + path_bill
        mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        sign = base64.b64encode(mac.digest()).decode('utf-8')
        headers['ACCESS-TIMESTAMP'] = timestamp
        headers['ACCESS-SIGN'] = sign
        
        bills = []
        async with session.get(url_base + path_bill, headers=headers) as resp:
            res_bill = await resp.json()
            if res_bill.get('code') == '00000' and res_bill.get('data'):
                bills = res_bill['data'].get('bills', [])
                
        # Also let's query fills from 2026-08-19 to 2026-08-21 just in case
        print(f"Total fills found on 2026-08-20 KST: {len(fills)}")
        print(f"Total bills found on 2026-08-20 KST: {len(bills)}")
        
        total_trade_fee = 0.0
        fee_by_trades = []
        for f in fills:
            # fee field in Bitget fills
            fee = abs(float(f.get('feeDetail', [{}])[0].get('fee', f.get('fee', 0)) if isinstance(f.get('feeDetail'), list) and len(f.get('feeDetail')) > 0 else f.get('fee', 0)))
            side = f.get('side')
            price = f.get('price')
            size = f.get('size')
            c_time = datetime.fromtimestamp(int(f.get('cTime', 0))/1000, tz=kst).strftime('%Y-%m-%d %H:%M:%S')
            fee_by_trades.append({
                'time': c_time,
                'side': side,
                'price': price,
                'size': size,
                'fee': fee
            })
            total_trade_fee += fee
            
        print("\n--- FILLS SUMMARY ---")
        for ft in fee_by_trades:
            print(f"[{ft['time']}] {ft['side'].upper()} {ft['size']} BTC @ ${ft['price']} | Fee: {ft['fee']:.4f} USDT")
        print(f"TOTAL TRADING FEES: {total_trade_fee:.4f} USDT")
        
        # Check bills breakdown
        funding_fee_total = 0.0
        bill_fee_total = 0.0
        print("\n--- BILLS SUMMARY ---")
        for b in bills:
            b_type = b.get('businessType', b.get('type', ''))
            amount = float(b.get('amount', 0))
            b_time = datetime.fromtimestamp(int(b.get('cTime', 0))/1000, tz=kst).strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{b_time}] Type: {b_type} | Amount: {amount} USDT | Balance: {b.get('balance')}")
            if 'fee' in b_type.lower() or 'trans' in b_type.lower():
                bill_fee_total += abs(amount)
            if 'fund' in b_type.lower():
                funding_fee_total += amount
                
        print(f"\nAGGREGATED SUMMARY FOR 2026-08-20 KST:")
        print(f"Total Trading Fees: {total_trade_fee:.4f} USDT (KRW: ~{total_trade_fee*1410:,.0f} won)")
        if funding_fee_total != 0:
            print(f"Funding Fee (Net): {funding_fee_total:.4f} USDT")

asyncio.run(get_fills_and_bills())