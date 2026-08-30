import asyncio, os, json, ccxt.async_support as ccxt

def get_env():
    env = {}
    if os.path.exists('/home/ubuntu/.env'):
        with open('/home/ubuntu/.env', 'r', encoding='utf-8') as f:
            for l in f:
                if '=' in l and not l.startswith('#'):
                    k, v = l.strip().split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get('BITGET_API_KEY') and os.path.exists('/home/ubuntu/server_config.json'):
        with open('/home/ubuntu/server_config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            env['BITGET_API_KEY'] = cfg.get('BITGET_API_KEY') or cfg.get('api_key')
            env['BITGET_SECRET_KEY'] = cfg.get('BITGET_SECRET_KEY') or cfg.get('secret_key') or cfg.get('secret')
            env['BITGET_PASSPHRASE'] = cfg.get('BITGET_PASSPHRASE') or cfg.get('passphrase')
    return env

async def main():
    env = get_env()
    ex = ccxt.bitget({
        'apiKey': env.get('BITGET_API_KEY'),
        'secret': env.get('BITGET_SECRET_KEY'),
        'password': env.get('BITGET_PASSPHRASE'),
        'options': {'defaultType': 'swap'}
    })
    positions = await ex.fetch_positions(['BTC/USDT:USDT'])
    active = [p for p in positions if float(p.get('contracts', 0) or 0) > 0]
    print('=== [LIVE ACTIVE POSITION] ===')
    for p in active:
        print(f"Side: {p['side'].upper()} | Contracts: {p['contracts']} BTC | EntryPrice: ${float(p['entryPrice']):,.2f} | UnrealizedPnL: ${float(p.get('unrealizedPnl') or 0):,.2f} USDT")
        print(json.dumps(p, ensure_ascii=False, indent=2))
    if not active:
        print("현재 활성화된 포지션이 없습니다 (No Active Position).")
    await ex.close()

if __name__ == '__main__':
    asyncio.run(main())
