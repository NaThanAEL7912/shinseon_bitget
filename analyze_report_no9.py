import urllib.request, json
import pandas as pd
import numpy as np
import paramiko
import datetime

def get_candles(gran, limit=100):
    url = f'https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity={gran}&productType=USDT-FUTURES&limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))['data']
        df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'baseVol', 'quoteVol'])
        df['ts_num'] = df['ts'].astype('int64')
        df['ts'] = pd.to_datetime(df['ts_num'], unit='ms')
        # KST 변환 (+9h)
        df['ts_kst'] = df['ts'] + pd.Timedelta(hours=9)
        for col in ['open', 'high', 'low', 'close', 'baseVol', 'quoteVol']:
            df[col] = df[col].astype(float)
        df = df.sort_values('ts').reset_index(drop=True)
        return df

def analyze_tf(df, name, n=5):
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

    print(f"=== {name} ===")
    for idx in range(-n, 0):
        row = df.iloc[idx]
        t = row['ts_kst'].strftime('%m-%d %H:%M')
        print(f"[{t}] O: {row['open']:,.1f} | H: {row['high']:,.1f} | L: {row['low']:,.1f} | C: {row['close']:,.1f} | Vol: {row['baseVol']:,.1f} | MA5: {row['ma5']:,.1f} | MA10: {row['ma10']:,.1f} | MA20: {row['ma20']:,.1f} | MA60: {row['ma60']:,.1f} | BB: [{row['bb_lower']:,.1f} ~ {row['bb_upper']:,.1f}] | RSI: {row['rsi14']:.1f}")
    print()

def main():
    print(f"=== KST Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 1. Ticker
    t_url = 'https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES'
    req = urllib.request.Request(t_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        ticker = json.loads(resp.read().decode('utf-8'))['data'][0]
    
    print(f"Last Price: {float(ticker['lastPr']):,.2f} | Mark: {float(ticker['markPrice']):,.2f} | Index: {float(ticker['indexPrice']):,.2f}")
    print(f"24h High: {float(ticker['high24h']):,.1f} | Low: {float(ticker['low24h']):,.1f} | Vol: {float(ticker['baseVolume']):,.2f} BTC | Turnover: {float(ticker['usdtVolume']):,.1f} USDT")
    funding = float(ticker.get('fundingRate', 0)) * 100
    oi = float(ticker.get('holdingAmount', 0))
    print(f"Funding Rate: {funding:+.4f}% | Bitget OI: {oi:,.2f} BTC (~${oi*float(ticker['lastPr']):,.0f})")
    print()

    # 2. Timeframes
    analyze_tf(get_candles('5m', 100), '5-Minute (5m)', 5)
    analyze_tf(get_candles('15m', 100), '15-Minute (15m)', 6)
    analyze_tf(get_candles('1H', 100), '1-Hour (1H)', 6)
    analyze_tf(get_candles('4H', 100), '4-Hour (4H)', 5)
    analyze_tf(get_candles('1D', 100), '1-Day (1D)', 5)

    # 3. Orderflow and Position
    key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)

    stdin, stdout, stderr = ssh.exec_command('python3 /home/ubuntu/temp_check_status.py')
    print("=== AWS TOKYO POSITION & ORDERS ===")
    print(stdout.read().decode('utf-8'))

    stdin, stdout, stderr = ssh.exec_command('tail -n 15 /home/ubuntu/docs/historical_data/orderflow_history_2026-08-28.csv')
    print("=== AWS TOKYO ORDERFLOW (15 ROWS) ===")
    print(stdout.read().decode('utf-8'))

    ssh.close()

if __name__ == '__main__':
    main()
