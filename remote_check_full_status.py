import paramiko

key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)

py_code = """
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
    
    try:
        positions = await ex.fetch_positions(['BTC/USDT:USDT'])
        for p in positions:
            if float(p.get('contracts', 0) or 0) > 0:
                print(f"ACTIVE POSITION: {p['side']} {p['contracts']} BTC @ {p['entryPrice']} | UnPnL: {p.get('unrealizedPnl')} | Liq: {p.get('liquidationPrice')}")
    finally:
        await ex.close()

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
            print('PLAN ORDERS (profit_loss):')
            print(json.dumps(data, indent=2, ensure_ascii=False))

asyncio.run(main())
"""

sftp = ssh.open_sftp()
with sftp.file('/home/ubuntu/temp_check_status.py', 'w') as f:
    f.write(py_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/ubuntu/temp_check_status.py')
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))

ssh.close()
