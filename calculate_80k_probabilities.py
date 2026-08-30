import urllib.request, json, time

def calculate_realtime_probabilities():
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    def fetch_json(url):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
            
    try:
        # 1. 24h Ticker & Mark Price
        tick = fetch_json("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        cur_p = float(tick['lastPrice'])
        h24 = float(tick['highPrice'])
        l24 = float(tick['lowPrice'])
        
        # 2. Premium & Funding
        fr_data = fetch_json("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT")
        fund_rate = float(fr_data.get('lastFundingRate', 0)) * 100
        
        # 3. Orderbook Depth 20 & 100
        d20 = fetch_json("https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=20")
        bids_20 = sum(float(b[1]) for b in d20['bids'])
        asks_20 = sum(float(a[1]) for a in d20['asks'])
        ratio_20 = bids_20 / (bids_20 + asks_20) * 100
        
        d100 = fetch_json("https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=100")
        bids_100 = sum(float(b[1]) for b in d100['bids'])
        asks_100 = sum(float(a[1]) for a in d100['asks'])
        ratio_100 = bids_100 / (bids_100 + asks_100) * 100
        
        # 4. Multi-Timeframe CVD (5m, 15m, 1h)
        k1m = fetch_json("https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=15")
        
        # 5m stat
        k5 = k1m[-5:]
        vol_5 = sum(float(k[5]) for k in k5)
        tb_5 = sum(float(k[9]) for k in k5)
        buy_pct_5 = (tb_5 / vol_5 * 100) if vol_5 > 0 else 50
        cvd_5 = tb_5 - (vol_5 - tb_5)
        dp_5 = float(k5[-1][4]) - float(k5[0][1])
        
        # 15m stat
        vol_15 = sum(float(k[5]) for k in k1m)
        tb_15 = sum(float(k[9]) for k in k1m)
        buy_pct_15 = (tb_15 / vol_15 * 100) if vol_15 > 0 else 50
        cvd_15 = tb_15 - (vol_15 - tb_15)
        dp_15 = float(k1m[-1][4]) - float(k1m[0][1])
        
        # 5. Moving Averages (15m & 1h)
        k15m = fetch_json("https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=15m&limit=30")
        c15 = [float(k[4]) for k in k15m]
        ma7_15m = sum(c15[-7:]) / 7
        ma25_15m = sum(c15[-25:]) / 25
        
        k1h = fetch_json("https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=30")
        c1h = [float(k[4]) for k in k1h]
        ma7_1h = sum(c1h[-7:]) / 7
        ma25_1h = sum(c1h[-25:]) / 25
        
        # 6. Scientific Probability Score Formulation
        # Factors:
        # F1: Depth Imbalance (20 & 100 levels) -> Weight 25%
        # F2: Short-term Taker CVD (5m & 15m) -> Weight 30%
        # F3: Moving Average Structure (Above 15m MA25, Distance to 1H MA25) -> Weight 25%
        # F4: Momentum & Rebound Strength (From low $77,835) -> Weight 20%
        
        score_depth = min(100, max(0, ratio_20 * 0.6 + ratio_100 * 0.4))
        score_cvd = min(100, max(0, buy_pct_5 * 0.6 + buy_pct_15 * 0.4))
        
        ma_score = 50.0
        if cur_p > ma25_15m:
            ma_score += 15.0
        if cur_p > ma7_15m:
            ma_score += 10.0
        if cur_p >= ma25_1h:
            ma_score += 15.0
        else:
            ma_score -= 10.0 # Resistance right above
            
        mom_score = 50.0
        rebound_from_low = cur_p - 77835.0
        if rebound_from_low > 70:
            mom_score += 20.0
        elif rebound_from_low > 30:
            mom_score += 10.0
            
        up_prob = (score_depth * 0.25) + (score_cvd * 0.30) + (ma_score * 0.25) + (mom_score * 0.20)
        up_prob = min(88.0, max(12.0, up_prob)) # Cap extreme probabilities
        down_prob = 100.0 - up_prob
        
        print("=== [SHINSEON ORDERFLOW PROBABILITY METRICS] ===")
        print(f"Current Price: ${cur_p:,.2f}")
        print(f"24h Range: ${l24:,.1f} ~ ${h24:,.1f}")
        print(f"Funding Rate: {fund_rate:+.4f}%")
        print(f"Depth 20 Ratio: {ratio_20:.1f}% Buy | Depth 100 Ratio: {ratio_100:.1f}% Buy")
        print(f"5m CVD: {cvd_5:+.1f} BTC (Taker Buy: {buy_pct_5:.1f}%, dP: {dp_5:+.1f}$)")
        print(f"15m CVD: {cvd_15:+.1f} BTC (Taker Buy: {buy_pct_15:.1f}%, dP: {dp_15:+.1f}$)")
        print(f"15m MA: MA7=${ma7_15m:,.1f} / MA25=${ma25_15m:,.1f}")
        print(f"1H MA:  MA7=${ma7_1h:,.1f} / MA25=${ma25_1h:,.1f}")
        print("--------------------------------------------------")
        print(f"★ CALCULATED UPWARD PROBABILITY (상방 확률): {up_prob:.1f}%")
        print(f"★ CALCULATED DOWNWARD PROBABILITY (하방 확률): {down_prob:.1f}%")
        print("==================================================")
        
    except Exception as e:
        print("Error calculating probabilities:", e)

if __name__ == "__main__":
    calculate_realtime_probabilities()