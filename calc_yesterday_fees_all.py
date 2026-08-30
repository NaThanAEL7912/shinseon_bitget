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

async def calculate_all_fees():
    env = get_env()
    api_key = env.get('BITGET_API_KEY')
    secret_key = env.get('BITGET_SECRET_KEY')
    passphrase = env.get('BITGET_PASSPHRASE')
    
    url_base = "https://api.bitget.com"
    kst = timezone(timedelta(hours=9))
    start_dt = datetime(2026, 8, 20, 0, 0, 0, tzinfo=kst)
    end_dt = datetime(2026, 8, 20, 23, 59, 59, 999000, tzinfo=kst)
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    all_fills = []
    curr_end_ts = end_ts
    
    async with aiohttp.ClientSession() as session:
        while True:
            path = f"/api/v2/mix/order/fills?symbol=BTCUSDT&productType=USDT-FUTURES&startTime={start_ts}&endTime={curr_end_ts}&limit=100"
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
            async with session.get(url_base + path, headers=headers) as resp:
                res = await resp.json()
                fill_list = res.get('data', {}).get('fillList', []) if res.get('code') == '00000' else []
                if not fill_list:
                    break
                all_fills.extend(fill_list)
                if len(fill_list) < 100:
                    break
                # Find oldest cTime in this batch
                oldest_cTime = min(int(x.get('cTime', curr_end_ts)) for x in fill_list)
                if oldest_cTime <= start_ts or oldest_cTime >= curr_end_ts:
                    break
                curr_end_ts = oldest_cTime - 1
                await asyncio.sleep(0.1)

    # Deduplicate by tradeId
    seen = set()
    unique_fills = []
    for f in all_fills:
        tid = f.get('tradeId')
        if tid not in seen:
            seen.add(tid)
            unique_fills.append(f)
            
    # Calculate total fee and breakdown
    total_fee_usdt = 0.0
    total_volume_btc = 0.0
    total_quote_volume = 0.0
    order_map = {}
    
    for f in unique_fills:
        oid = f.get('orderId')
        fee = 0.0
        fee_details = f.get('feeDetail', [])
        if isinstance(fee_details, list) and len(fee_details) > 0:
            for fd in fee_details:
                fee += abs(float(fd.get('totalFee', 0)))
        else:
            fee = abs(float(f.get('fee', 0)))
            
        base_vol = float(f.get('baseVolume', 0))
        quote_vol = float(f.get('quoteVolume', 0))
        price = float(f.get('price', 0))
        cTime = int(f.get('cTime', 0))
        time_str = datetime.fromtimestamp(cTime/1000, tz=kst).strftime('%Y-%m-%d %H:%M:%S')
        side = f.get('side', '')
        trade_side = f.get('tradeSide', '')
        trade_scope = f.get('tradeScope', '')
        
        total_fee_usdt += fee
        total_volume_btc += base_vol
        total_quote_volume += quote_vol
        
        if oid not in order_map:
            order_map[oid] = {
                'time': time_str,
                'side': side,
                'trade_side': trade_side,
                'trade_scope': trade_scope,
                'price': price,
                'base_vol': 0.0,
                'quote_vol': 0.0,
                'fee': 0.0
            }
        order_map[oid]['base_vol'] += base_vol
        order_map[oid]['quote_vol'] += quote_vol
        order_map[oid]['fee'] += fee
        
    print(f"=== 2026-08-20 (어저께) 비트겟 수수료 완전 결산 ===")
    print(f"총 체결 건수 (Fills): {len(unique_fills)}건")
    print(f"총 주문 건수 (Orders): {len(order_map)}건")
    print(f"총 거래량 (BTC): {total_volume_btc:.4f} BTC")
    print(f"총 거래대금 (USD): ${total_quote_volume:,.2f} USD")
    print(f"\n★ 총 지출 수수료: ${total_fee_usdt:,.4f} USDT")
    print(f"★ 한화 환산 (1,410원/USD): 약 {total_fee_usdt * 1410:,.0f} 원\n")
    
    print("--- 주요 주문별 수수료 내역 ---")
    for oid, oinfo in sorted(order_map.items(), key=lambda x: x[1]['time']):
        print(f"[{oinfo['time']}] {oinfo['side'].upper()} {oinfo['trade_side']} {oinfo['base_vol']:.4f} BTC @ ${oinfo['price']:,.1f} | Fee: ${oinfo['fee']:.4f} USDT ({oinfo['trade_scope']})")

asyncio.run(calculate_all_fees())