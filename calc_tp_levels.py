import requests

r = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5)
data = r.json()
t_info = data["data"][0]
mark_p = float(t_info.get("markPrice", 0.0) or t_info.get("lastPr", 0.0) or 0.0)

entry_p = 76910.0
lev = 30
roe = (mark_p - entry_p) / entry_p * lev * 100.0
pnl_pct = (mark_p - entry_p) / entry_p * 100.0

print(f"Current BTC Price: ${mark_p:,.2f}")
print(f"Entry Price: ${entry_p:,.2f}")
print(f"Current PnL: {pnl_pct:+.2f}% (ROE 30x: {roe:+.2f}%)")

# Calculate key target levels
tp_scalp = entry_p * (1 + 0.0055)  # 직전 고점 저항
tp_london_1 = entry_p * (1 + 0.0080) # 유럽 정통 1차 (+0.8%)
tp_london_2 = entry_p * (1 + 0.0100) # 유럽 정통 1차 (+1.0%)
tp_london_kill = entry_p * (1 + 0.0120) # 유럽 올킬 (+1.2%)

print(f"1. [직전 고점 안전 분할익절 (+0.55%)]: ${tp_scalp:,.1f} (ROE +16.5%)")
print(f"2. [유럽 세션 1차 표준익절 (+0.80%)]: ${tp_london_1:,.1f} (ROE +24.0%)")
print(f"3. [유럽 세션 1차 황금익절 (+1.00%)]: ${tp_london_2:,.1f} (ROE +30.0%)")
print(f"4. [유럽 세션 2차 올킬익절 (+1.20%)]: ${tp_london_kill:,.1f} (ROE +36.0%)")