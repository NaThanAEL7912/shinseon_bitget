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

def load_credentials():
    cfg = {}
    
    # 1. Try local .env
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        cfg[k.strip()] = v.strip().strip('"').strip("'")
        except Exception as e:
            print(f"[Warning] Failed to read .env: {e}")

    # 2. Try server_config.json if keys not complete
    if not (cfg.get("BITGET_API_KEY") and cfg.get("BITGET_SECRET_KEY") and cfg.get("BITGET_PASSPHRASE")):
        for sc_path in ["server_config.json", "/home/ubuntu/server_config.json", "c:\\Working\\ShinSeon_Bitget\\server_config.json"]:
            if os.path.exists(sc_path):
                try:
                    with open(sc_path, "r", encoding="utf-8") as f:
                        sc = json.load(f)
                        for k in ["BITGET_API_KEY", "BITGET_SECRET_KEY", "BITGET_PASSPHRASE"]:
                            if sc.get(k):
                                cfg[k] = sc[k]
                except Exception as e:
                    print(f"[Warning] Failed to read {sc_path}: {e}")

    api_key = cfg.get("BITGET_API_KEY")
    secret_key = cfg.get("BITGET_SECRET_KEY")
    passphrase = cfg.get("BITGET_PASSPHRASE")

    if not (api_key and secret_key and passphrase):
        raise ValueError("Bitget API credentials could not be loaded!")

    return api_key, secret_key, passphrase

def make_request(method, path, body_dict=None, api_key=None, secret_key=None, passphrase=None):
    url_base = "https://api.bitget.com"
    body_str = json.dumps(body_dict) if body_dict is not None else ""
    ts = str(int(time.time() * 1000))
    msg = ts + method.upper() + path + body_str
    mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode('utf-8')
    headers = {
        'ACCESS-KEY': api_key,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': ts,
        'ACCESS-PASSPHRASE': passphrase,
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

def execute_two_sl_78500_78400():
    print("================================================================================")
    print("🛡️ [신선 비트겟] 50% 분할 손절 방패 2단 발주 ($78,500.0 / $78,400.0) 집행")
    print("================================================================================")
    
    api_key, secret_key, passphrase = load_credentials()
    print(f"🔑 API 인증키 로드 완료 (API_KEY: {api_key[:4]}****{api_key[-4:]})")

    # 1. Check live position
    path_pos = "/api/v2/mix/position/all-position?productType=USDT-FUTURES"
    pos_res = make_request("GET", path_pos, api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    pos_data = pos_res.get("data", [])
    btc_pos = next((p for p in pos_data if p.get("symbol") == "BTCUSDT" and float(p.get("total", 0)) > 0), None)
    
    if not btc_pos:
        print("❌ [경고] 현재 활성화된 BTC 포지션이 없습니다!")
        print(f"전체 포지션 응답: {pos_res}")
        return
        
    total_qty = float(btc_pos.get("total", 0))
    entry_p = float(btc_pos.get("openPriceAvg", 0))
    side = btc_pos.get("holdSide", "long")
    lev = btc_pos.get("leverage")
    pnl = float(btc_pos.get("unrealizedPL", 0))
    print(f"📊 [현재 실시간 포지션] {side.upper()} {total_qty} BTC | 평단가: ${entry_p:,.2f} | 레버리지: {lev}x | 미실현손익: {pnl:+.2f} USDT")

    # Check current mark price
    t_res = requests.get("https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES", timeout=5).json()
    mark_p = float(t_res['data'][0].get('markPrice', 0))
    print(f"📈 [현재 시장 마크가] ${mark_p:,.2f}")

    # 2. Query pending plan orders and cancel all previous loss/stop orders
    print("\n🧹 [1단계] 기존 잔여 손절 플랜 주문(loss_plan, pos_loss) 정밀 정화 진행...")
    path_pending = "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss"
    pending_res = make_request("GET", path_pending, api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    entrusted = (pending_res.get("data") or {}).get("entrustedList") or []
    
    cancelled_count = 0
    path_cancel = "/api/v2/mix/order/cancel-plan-order"
    for o in entrusted:
        plan_type = o.get("planType")
        oid = o.get("orderId")
        # 손절 주문들(loss_plan, pos_loss) 취소 정화
        if plan_type in ["loss_plan", "pos_loss"]:
            body_cancel = {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "orderId": str(oid),
                "planType": plan_type
            }
            c_res = make_request("POST", path_cancel, body_dict=body_cancel, api_key=api_key, secret_key=secret_key, passphrase=passphrase)
            print(f"   ↳ 기존 손절 주문 취소 [OrderID: {oid}, Type: {plan_type}, Trigger: ${o.get('triggerPrice')}]: code={c_res.get('code')}, msg={c_res.get('msg')}")
            cancelled_count += 1
            time.sleep(0.1)

    print(f"   🧹 기존 손절 플랜 주문 총 {cancelled_count}건 정화 완료!")
    time.sleep(0.5)

    # 3. Place Two-Stage Stop Loss Orders
    # 명세:
    # 1차 손절: 1.2284 BTC @ $78,500.0 (loss_plan, mark_price, holdSide: long)
    # 2차 손절: 1.2285 BTC @ $78,400.0 (loss_plan, mark_price, holdSide: long)
    print("\n🚀 [2단계] 비트겟 공식 V2 TPSL API를 통한 50% 분할 손절 2단 신규 발주...")
    
    sl_orders = [
        {
            "name": "🛡️ 1차 50% 손절 방패",
            "body": {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "loss_plan",
                "triggerPrice": "78500.0",
                "triggerType": "mark_price",
                "size": "1.2284",
                "holdSide": "long"
            }
        },
        {
            "name": "🛡️ 2차 50% 손절 방패",
            "body": {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "loss_plan",
                "triggerPrice": "78400.0",
                "triggerType": "mark_price",
                "size": "1.2285",
                "holdSide": "long"
            }
        }
    ]

    path_place = "/api/v2/mix/order/place-tpsl-order"
    results = []

    for item in sl_orders:
        name = item["name"]
        body = item["body"]
        print(f"   ▶ {name} 발주 중... (수량: {body['size']} BTC @ 트리거가: ${body['triggerPrice']})")
        res = make_request("POST", path_place, body_dict=body, api_key=api_key, secret_key=secret_key, passphrase=passphrase)
        print(f"     거래소 응답: code={res.get('code')}, msg={res.get('msg')}, data={res.get('data')}")
        results.append({
            "name": name,
            "body": body,
            "response": res
        })
        time.sleep(0.3)

    # 4. Verify Pending Plan Orders
    print("\n🔍 [3단계] 거래소 대기 플랜 주문 최종 검증 조회...")
    pending_res_final = make_request("GET", path_pending, api_key=api_key, secret_key=secret_key, passphrase=passphrase)
    final_list = (pending_res_final.get("data") or {}).get("entrustedList") or []
    
    print(f"   ↳ 현재 활성화된 대기 플랜 주문 수: {len(final_list)}개")
    for idx, p_order in enumerate(final_list, 1):
        order_id = p_order.get("orderId")
        p_type = p_order.get("planType")
        t_price = p_order.get("triggerPrice")
        sz = p_order.get("size")
        h_side = p_order.get("posSide") or p_order.get("holdSide")
        status = p_order.get("planStatus", "live")
        print(f"     [{idx}] OrderID: {order_id} | Type: {p_type} | HoldSide: {h_side} | Trigger: ${t_price} | Size: {sz} BTC | Status: {status}")

    print("\n================================================================================")
    all_success = all(r["response"].get("code") == "00000" for r in results)
    if all_success:
        print("✅ [발주 대성공] 50% 분할 손절 방패 2단이 거래소에 완벽히 안착되었습니다! (code: 00000)")
        for r in results:
            oid = r["response"].get("data", {}).get("orderId")
            print(f"   - {r['name']}: OrderID={oid}, Size={r['body']['size']} BTC, Trigger=${r['body']['triggerPrice']}")
    else:
        print("⚠️ [발주 결과 확인 필요] 일부 주문 응답 코드가 00000이 아닙니다.")
    print("================================================================================")

    return results, final_list

if __name__ == "__main__":
    execute_two_sl_78500_78400()
