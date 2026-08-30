import os
import sys
import json
import time
import hmac
import hashlib
import base64
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

accounts = {
    "Master Account (국왕 폐하 본 계정)": {
        "api_key": "bg_670c7963afe129099346583180ce606b",
        "secret_key": "4fe82e41304e84e315c7aa222ead7a4307182ec5f4766c37ad2290bf4268a2a0",
        "passphrase": "shinsun1234567"
    },
    "Sub Account (shinseon_bot 서브 계정)": {
        "api_key": "bg_b44a5deefebebd0e2bd63e5c7d3a0e66",
        "secret_key": "ad87f442600798bc813666de895a655f87fc34e5d06461c39c7bc7e7c5d87935",
        "passphrase": "shinseonbot1234567"
    }
}

def make_request(method, path, body_dict=None, cred=None):
    url_base = "https://api.bitget.com"
    body_str = json.dumps(body_dict) if body_dict is not None else ""
    ts = str(int(time.time() * 1000))
    msg = ts + method.upper() + path + body_str
    mac = hmac.new(cred["secret_key"].encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': cred["api_key"],
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': cred["passphrase"],
        'Content-Type': 'application/json',
        'locale': 'ko-KR'
    }
    url = url_base + path
    if method.upper() == "GET":
        resp = requests.get(url, headers=headers, timeout=10)
    elif method.upper() == "POST":
        resp = requests.post(url, headers=headers, data=body_str, timeout=10)
    else:
        raise ValueError(f"Unsupported method: {method}")
    return resp.json()

def check_account(name, cred):
    print(f"\n=======================================================")
    print(f"[Checking] {name}")
    print(f"   API Key: {cred['api_key'][:6]}****{cred['api_key'][-4:]}")
    print(f"=======================================================")
    
    # 1. Position
    pos = make_request("GET", "/api/v2/mix/position/all-position?productType=USDT-FUTURES", cred=cred)
    pos_data = pos.get("data", [])
    print(f"Positions response code: {pos.get('code')}, count: {len(pos_data)}")
    for p in pos_data:
        total = float(p.get("total", 0))
        if total > 0:
            print(f"   👉 Symbol: {p.get('symbol')}, Side: {p.get('holdSide')}, Size: {total} BTC, AvgPrice: ${float(p.get('openPriceAvg', 0)):,.2f}, LiqPrice: ${float(p.get('liquidationPrice', 0)):,.2f}, PnL: ${float(p.get('unrealizedPL', 0)):+,.2f} USDT, Lev: {p.get('leverage')}x")

    # 2. Account balance
    acc = make_request("GET", "/api/v2/mix/account/accounts?productType=USDT-FUTURES", cred=cred)
    acc_data = acc.get("data", [])
    for a in acc_data:
        print(f"💰 Balance: Equity=${float(a.get('accountEquity', 0)):,.2f} USDT, Available=${float(a.get('available', 0)):,.2f} USDT, UnrealizedPL=${float(a.get('unrealizedPL', 0)):+,.2f} USDT")

    # 3. Pending Plan Orders
    plans = make_request("GET", "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss", cred=cred)
    entrusted = (plans.get("data") or {}).get("entrustedList") or []
    print(f"Pending Plan Orders (profit_loss): {len(entrusted)}")
    for o in entrusted:
        print(f"   ↳ OrderID: {o.get('orderId')}, PlanType: {o.get('planType')}, HoldSide: {o.get('posSide') or o.get('holdSide')}, Trigger: ${o.get('triggerPrice')}, Size: {o.get('size')} BTC, Status: {o.get('planStatus')}")

def main():
    for name, cred in accounts.items():
        check_account(name, cred)

if __name__ == "__main__":
    main()
