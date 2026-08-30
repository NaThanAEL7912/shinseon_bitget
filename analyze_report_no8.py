import urllib.request, json
import pandas as pd
import numpy as np
import paramiko
import sys

def get_df(gran, limit=65):
    url = f'https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity={gran}&productType=USDT-FUTURES&limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))['data']
        df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'baseVol', 'quoteVol'])
        df['ts'] = pd.to_datetime(df['ts'].astype('int64'), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'baseVol', 'quoteVol']:
            df[col] = df[col].astype(float)
        df = df.sort_values('ts').reset_index(drop=True)
        return df

def analyze_tf(df, name):
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma120'] = df['close'].rolling(120).mean() if len(df) >= 120 else np.nan
    df['std20'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['ma20'] + (df['std20'] * 2)
    df['bb_mid'] = df['ma20']
    df['bb_lower'] = df['ma20'] - (df['std20'] * 2)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi14'] = 100 - (100 / (1 + rs))
    
    print(f"=== {name} Analysis ===")
    for idx in range(-5, 0):
        row = df.iloc[idx]
        print(f"[{row['ts']}] O: {row['open']:.1f}, H: {row['high']:.1f}, L: {row['low']:.1f}, C: {row['close']:.1f} | MA5: {row['ma5']:.1f}, MA10: {row['ma10']:.1f}, MA20: {row['ma20']:.1f}, MA60: {row['ma60']:.1f}, BB: [{row['bb_lower']:.1f} ~ {row['bb_upper']:.1f}], RSI: {row['rsi14']:.1f}")
    print()

def main():
    analyze_tf(get_df('15m', 100), '15-Minute (15m)')
    analyze_tf(get_df('1H', 100), '1-Hour (1H)')
    analyze_tf(get_df('4H', 100), '4-Hour (4H)')
    analyze_tf(get_df('1D', 100), '1-Day (1D)')

    # AWS Orderflow tail & bot log check & open orders / position check
    key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)
    
    stdin, stdout, stderr = ssh.exec_command('tail -n 20 /home/ubuntu/docs/historical_data/orderflow_history_2026-08-28.csv')
    print("=== [AWS TOKYO LATEST ORDERFLOW (20 ROWS)] ===")
    print(stdout.read().decode('utf-8'))
    
    stdin, stdout, stderr = ssh.exec_command('tail -n 35 /home/ubuntu/nohup.out')
    print("=== [AWS TOKYO LATEST NOHUP LOG (35 ROWS)] ===")
    print(stdout.read().decode('utf-8'))

    stdin, stdout, stderr = ssh.exec_command('tail -n 30 /home/ubuntu/bot_trade.log')
    print("=== [AWS TOKYO LATEST BOT_TRADE LOG (30 ROWS)] ===")
    print(stdout.read().decode('utf-8'))

    ssh.close()

if __name__ == '__main__':
    main()
