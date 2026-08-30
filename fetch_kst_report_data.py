import urllib.request, json
import pandas as pd
import numpy as np

def get_df(gran, limit=100):
    url = f'https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity={gran}&productType=USDT-FUTURES&limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))['data']
        df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'baseVol', 'quoteVol'])
        df['ts'] = pd.to_datetime(df['ts'].astype('int64'), unit='ms') + pd.Timedelta(hours=9) # KST
        for col in ['open', 'high', 'low', 'close', 'baseVol', 'quoteVol']:
            df[col] = df[col].astype(float)
        df = df.sort_values('ts').reset_index(drop=True)
        return df

def get_indicators(df):
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
    return df

df15 = get_indicators(get_df('15m', 100))
df1h = get_indicators(get_df('1H', 100))
df4h = get_indicators(get_df('4H', 100))
df1d = get_indicators(get_df('1D', 100))

print("=== 15m LATEST 3 CANDLES (KST) ===")
print(df15[['ts', 'open', 'high', 'low', 'close', 'ma5', 'ma10', 'ma20', 'ma60', 'bb_lower', 'bb_upper', 'rsi14']].tail(3).to_string())

print("\n=== 1H LATEST 3 CANDLES (KST) ===")
print(df1h[['ts', 'open', 'high', 'low', 'close', 'ma5', 'ma10', 'ma20', 'ma60', 'bb_lower', 'bb_upper', 'rsi14']].tail(3).to_string())

print("\n=== 4H LATEST 3 CANDLES (KST) ===")
print(df4h[['ts', 'open', 'high', 'low', 'close', 'ma5', 'ma10', 'ma20', 'ma60', 'bb_lower', 'bb_upper', 'rsi14']].tail(3).to_string())

print("\n=== 1D LATEST 2 CANDLES (KST) ===")
print(df1d[['ts', 'open', 'high', 'low', 'close', 'ma5', 'ma10', 'ma20', 'ma60', 'bb_lower', 'bb_upper', 'rsi14']].tail(2).to_string())
