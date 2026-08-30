import urllib.request
import json
import pandas as pd
import numpy as np

def fetch_candles(granularity, limit=50):
    url = f"https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity={granularity}&productType=USDT-FUTURES&limit={limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        raw = data.get('data', [])
        # Bitget candles: [ts, open, high, low, close, baseVol, quoteVol]
        df = pd.DataFrame(raw, columns=['ts', 'open', 'high', 'low', 'close', 'baseVol', 'quoteVol'])
        df['ts'] = pd.to_datetime(df['ts'].astype('int64'), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'baseVol', 'quoteVol']:
            df[col] = df[col].astype(float)
        df = df.sort_values('ts').reset_index(drop=True)
        return df

def calc_indicators(df):
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['std20'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['ma20'] + (df['std20'] * 2)
    df['bb_lower'] = df['ma20'] - (df['std20'] * 2)
    
    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi14'] = 100 - (100 / (1 + rs))
    return df

df_15m = calc_indicators(fetch_candles('15m', 50))
df_1h = calc_indicators(fetch_candles('1H', 50))

print("=== 15M CANDLES (LAST 5) ===")
print(df_15m[['ts', 'open', 'high', 'low', 'close', 'ma5', 'ma10', 'ma20', 'bb_upper', 'bb_lower', 'rsi14']].tail(5).to_string())

print("\n=== 1H CANDLES (LAST 5) ===")
print(df_1h[['ts', 'open', 'high', 'low', 'close', 'ma5', 'ma10', 'ma20', 'bb_upper', 'bb_lower', 'rsi14']].tail(5).to_string())
