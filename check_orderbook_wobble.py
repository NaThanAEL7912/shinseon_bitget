import requests

r_depth = requests.get("https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=BTCUSDT&productType=USDT-FUTURES&precision=scale&limit=10", timeout=5).json()
asks = r_depth.get("data", {}).get("asks", [])
bids = r_depth.get("data", {}).get("bids", [])

print("=== [실시간 호가창 매도벽(Asks) vs 매수벽(Bids)] ===")
print("Top Asks (매도벽):")
for a in asks[:5]:
    print(f"  ${float(a[0]):,.1f} : {float(a[1]):.3f} BTC")

print("\nTop Bids (매수벽):")
for b in bids[:5]:
    print(f"  ${float(b[0]):,.1f} : {float(b[1]):.3f} BTC")