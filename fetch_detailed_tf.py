import urllib.request, json
import pandas as pd
import numpy as np

def get_candles(gran, limit=100):
    url = f'https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity={gran}&productType=USDT-FUTURES&limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))['data']
        df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'baseVol', 'quoteVol'])
        df['ts'] = pd.to_datetime(df['ts'].astype('int64'), unit='ms') + pd.Timedelta(hours=9)
        for col in ['open', 'high', 'low', 'close', 'baseVol', 'quoteVol']:
            df[col] = df[col].astype(float)
        return df.sort_values('ts').reset_index(drop=True)

def print_detail(gran, name, n=8):
    df = get_candles(gran, 100)
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['std20'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['ma20'] + (df['std20'] * 2)
    df['bb_mid'] = df['ma20']
    df['bb_lower'] = df['ma20'] - (df['std20'] * 2)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi14'] = 100 - (100 / (1 + (gain/loss)))

    print(f"=== {name} ===")
    for idx in range(-n, 0):
        r = df.iloc[idx]
        t_str = r['ts'].strftime('%m-%d %H:%M')
        print(f"[{t_str}] 시가:{r['open']:,.1f} | 고가:{r['high']:,.1f} | 저가:{r['low']:,.1f} | 종가:{r['close']:,.1f} | 볼륨:{r['baseVol']:,.1f} BTC | MA5:{r['ma5']:,.1f} | MA10:{r['ma10']:,.1f} | MA20:{r['ma20']:,.1f} | MA60:{r['ma60']:,.1f} | 볼밴:[{r['bb_lower']:,.1f} ~ {r['bb_upper']:,.1f}] | RSI:{r['rsi14']:.1f}")
    print()

def main():
    print_detail('5m', '5-Minute (5m)', 8)
    print_detail('15m', '15-Minute (15m)', 8)
    print_detail('1H', '1-Hour (1H)', 8)

if __name__ == '__main__':
    main()
