import paramiko
import sys
import json
import urllib.request

def analyze():
    sys.stdout.reconfigure(encoding='utf-8')
    key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)
    
    # 1. Header and last 15 rows of orderflow
    stdin, stdout, stderr = ssh.exec_command('head -n 2 /home/ubuntu/docs/historical_data/orderflow_history_2026-08-28.csv && tail -n 15 /home/ubuntu/docs/historical_data/orderflow_history_2026-08-28.csv')
    print("=== [CSV HEADER & TAIL] ===")
    print(stdout.read().decode('utf-8'))
    
    # 2. Check position & state from server if any endpoint or log
    stdin, stdout, stderr = ssh.exec_command('grep -i "position" /home/ubuntu/shinseon.log | tail -n 10')
    print("=== [LOG POSITIONS] ===")
    print(stdout.read().decode('utf-8'))

    # 3. Check current price and candles via public bitget api
    # 15m candles
    url_15m = "https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity=15m&productType=USDT-FUTURES&limit=50"
    url_1h = "https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity=1H&productType=USDT-FUTURES&limit=50"
    url_ticker = "https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES"
    
    req = urllib.request.Request(url_ticker, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        ticker_data = json.loads(resp.read().decode('utf-8'))
        print("=== [TICKER DATA] ===")
        print(ticker_data)
        
    req_15m = urllib.request.Request(url_15m, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_15m) as resp:
        candles_15m = json.loads(resp.read().decode('utf-8'))
        print("=== [15M CANDLES COUNT] ===", len(candles_15m.get('data', [])))
        
    req_1h = urllib.request.Request(url_1h, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_1h) as resp:
        candles_1h = json.loads(resp.read().decode('utf-8'))
        print("=== [1H CANDLES COUNT] ===", len(candles_1h.get('data', [])))

    ssh.close()

if __name__ == '__main__':
    analyze()
