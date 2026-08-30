import requests

r_depth = requests.get("https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=10", timeout=5).json()
asks = r_depth.get("asks", [])
bids = r_depth.get("bids", [])

print("=== [BINANCE REAL-TIME FUTURES DEPTH] ===")
print("Asks (Resistance Walls):")
for a in asks[:5]:
    print(f"  ${float(a[0]):,.1f} : {float(a[1]):.3f} BTC")

print("\nBids (Support Walls):")
for b in bids[:5]:
    print(f"  ${float(b[0]):,.1f} : {float(b[1]):.3f} BTC")