import urllib.request, json
import pandas as pd
import numpy as np
import datetime

def get_candles(gran, limit=100):
    url = f'https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity={gran}&productType=USDT-FUTURES&limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))['data']
        df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'baseVol', 'quoteVol'])
        df['ts_num'] = df['ts'].astype('int64')
        df['ts'] = pd.to_datetime(df['ts_num'], unit='ms')
        df['ts_kst'] = df['ts'] + pd.Timedelta(hours=9)
        for col in ['open', 'high', 'low', 'close', 'baseVol', 'quoteVol']:
            df[col] = df[col].astype(float)
        df = df.sort_values('ts').reset_index(drop=True)
        return df

def analyze_tf(df, name, n=8):
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

def get_orderbook():
    url = 'https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=BTCUSDT&productType=USDT-FUTURES&limit=20&precision=scale0'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))['data']
            print("=== ORDERBOOK TOP 10 ===")
            print("Asks (Resistance):")
            for a in reversed(data['asks'][:10]):
                print(f"  ${float(a[0]):,.1f} : {float(a[1]):.3f} BTC")
            print("Bids (Support):")
            for b in data['bids'][:10]:
                print(f"  ${float(b[0]):,.1f} : {float(b[1]):.3f} BTC")
    except Exception as e:
        print(f"Orderbook error: {e}")

def get_trades_cvd():
    url = 'https://api.bitget.com/api/v2/mix/market/fills?symbol=BTCUSDT&productType=USDT-FUTURES&limit=100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))['data']
            buy_vol = sum(float(x['size']) for x in data if x['side'] == 'buy')
            sell_vol = sum(float(x['size']) for x in data if x['side'] == 'sell')
            print(f"=== RECENT 100 TRADES CVD ===")
            print(f"Buy Vol: {buy_vol:.3f} BTC | Sell Vol: {sell_vol:.3f} BTC | Net Delta: {buy_vol - sell_vol:+.3f} BTC (Buy Ratio: {buy_vol/(buy_vol+sell_vol)*100:.1f}%)")
    except Exception as e:
        print(f"Trades CVD error: {e}")

if __name__ == '__main__':
    analyze_tf(get_candles('5m', 100), '5-Minute (5m)', 8)
    analyze_tf(get_candles('15m', 100), '15-Minute (15m)', 8)
    analyze_tf(get_candles('1H', 100), '1-Hour (1H)', 8)
    get_orderbook()
    get_trades_cvd()
