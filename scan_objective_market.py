import requests

url_base = "https://api.bitget.com"

# 1. Ticker & Funding Rate
r_t = requests.get(f"{url_base}/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
t_data = r_t['data'][0]
mark_p = float(t_data.get('markPrice', 0))
fund_rate = float(t_data.get('fundingRate', 0)) * 100
h24 = float(t_data.get('high24h', 0))
l24 = float(t_data.get('low24h', 0))

# 2. Candles: 15m, 1H, 4H, 1D
def get_candles(gran, limit=30):
    r = requests.get(f"{url_base}/api/v2/mix/market/candles?symbol=BTCUSDT&productType=USDT-FUTURES&granularity={gran}&limit={limit}", timeout=5).json()
    return r.get('data') or []

c15 = get_candles("15m", 30)
c1h = get_candles("1H", 30)
c4h = get_candles("4H", 30)

def calc_ma(candles, period):
    closes = [float(c[4]) for c in candles[:period]]
    return sum(closes) / len(closes) if closes else 0

ma7_15m = calc_ma(c15, 7)
ma25_15m = calc_ma(c15, 25)

ma7_1h = calc_ma(c1h, 7)
ma25_1h = calc_ma(c1h, 25)

ma7_4h = calc_ma(c4h, 7)
ma25_4h = calc_ma(c4h, 25)

print(f"=== OBJECTIVE BITCOIN MARKET SCAN (Price: ${mark_p:,.2f}) ===")
print(f"- 24h High: ${h24:,.1f} | 24h Low: ${l24:,.1f} | Funding Rate: {fund_rate:+.4f}%")
print(f"- 15m MA7: ${ma7_15m:,.1f} | MA25: ${ma25_15m:,.1f} (vs Price: {mark_p - ma25_15m:+.1f})")
print(f"- 1H  MA7: ${ma7_1h:,.1f} | MA25: ${ma25_1h:,.1f} (vs Price: {mark_p - ma25_1h:+.1f})")
print(f"- 4H  MA7: ${ma7_4h:,.1f} | MA25: ${ma25_4h:,.1f} (vs Price: {mark_p - ma25_4h:+.1f})")