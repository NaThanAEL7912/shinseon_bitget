import json, os, sys, hmac, hashlib, base64, time, requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def execute_two_sl_short():
    cfg = {}
    env_paths = [
        ".env",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        r"C:\Working\ShinSeon_Bitget\.env"
    ]
    for p in env_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        cfg[k.strip()] = v.strip().strip('"').strip("'")
            if cfg.get("BITGET_API_KEY"):
                break
                    
    api_key = cfg.get("BITGET_API_KEY")
    secret_key = cfg.get("BITGET_SECRET_KEY")
    passphrase = cfg.get("BITGET_PASSPHRASE")
    
    url_base = "https://api.bitget.com"
    path_plan = "/api/v2/mix/order/place-tpsl-order"
    path_cancel = "/api/v2/mix/order/cancel-plan-order"
    path_list = "/api/v2/mix/order/orders-plan-pending"
    
    def get_headers(method, path_url, body_str=""):
        ts = str(int(time.time() * 1000))
        msg = ts + method.upper() + path_url + body_str
        mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
        sign = base64.b64encode(mac.digest()).decode('utf-8')
        return {
            'ACCESS-KEY': api_key,
            'ACCESS-SIGN': sign,
            'ACCESS-TIMESTAMP': ts,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }

    # 1. 기존 플랜 주문 조회 및 정화(취소)
    print("=== [1단계] 기존 잔여 플랜 주문 전량 정화(취소) 시작 ===")
    list_url = f"{path_list}?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss"
    headers_list = get_headers("GET", list_url, "")
    r_list = requests.get(url_base + list_url, headers=headers_list, timeout=10)
    existing_orders = r_list.json().get("data", {}).get("entrustedList", []) or []
    
    for order in existing_orders:
        oid = order.get("orderId")
        plan_t = order.get("planType") or "loss_plan"
        print(f"[기존 주문 취소 대상] OrderId={oid}, Trigger={order.get('triggerPrice')}, Size={order.get('size')}, PlanType={plan_t}")
        cancel_body_dict = {
            "symbol": "BTCUSDT",
            "productType": "USDT-FUTURES",
            "marginCoin": "USDT",
            "orderId": str(oid),
            "planType": plan_t
        }
        cancel_body = json.dumps(cancel_body_dict)
        headers_cancel = get_headers("POST", path_cancel, cancel_body)
        r_cancel = requests.post(url_base + path_cancel, headers=headers_cancel, data=cancel_body, timeout=10)
        print(f"  -> 취소 응답: {r_cancel.json()}")
        time.sleep(0.2)
        
    time.sleep(0.5)

    # 2. 1차 / 2차 분할 손절 방패 발주
    print("\n=== [2단계] 숏 포지션 50% 분할 손절 방패 2단 발주 시작 ===")
    # 1차 손절: 1.0259 BTC @ $78,800.0 (SHORT)
    sl1_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78800.0",
        "triggerType": "mark_price",
        "size": "1.0259",
        "holdSide": "short"
    }
    
    # 2차 손절: 1.0260 BTC @ $78,700.0 (SHORT)
    sl2_body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginCoin": "USDT",
        "planType": "loss_plan",
        "triggerPrice": "78700.0",
        "triggerType": "mark_price",
        "size": "1.0260",
        "holdSide": "short"
    }
    
    results = []
    for name, b_dict in [("1차 50% 숏 손절 방패 ($78,800.0 / 1.0259 BTC)", sl1_body), ("2차 50% 숏 손절 방패 ($78,700.0 / 1.0260 BTC)", sl2_body)]:
        b_json = json.dumps(b_dict)
        headers_order = get_headers("POST", path_plan, b_json)
        res = requests.post(url_base + path_plan, headers=headers_order, data=b_json, timeout=10)
        res_data = res.json()
        print(f"[{name}] 발주 응답: HTTP {res.status_code} | {res_data}")
        results.append((name, res_data))
        time.sleep(0.3)
        
    time.sleep(0.5)

    # 3. 최종 거래소 대기 주문 검증
    print("\n=== [3단계] 최종 비트겟 거래소 대기 주문 무결성 검증 ===")
    headers_verify = get_headers("GET", list_url, "")
    r_verify = requests.get(url_base + list_url, headers=headers_verify, timeout=10)
    final_orders = r_verify.json().get("data", {}).get("entrustedList", []) or []
    print(f"현재 비트겟 활성 대기 플랜 주문 수: {len(final_orders)}건")
    for fo in final_orders:
        print(f"  [확인] OrderId: {fo.get('orderId')} | PlanType: {fo.get('planType')} | TriggerPrice: ${fo.get('triggerPrice')} | Size: {fo.get('size')} BTC | Side: {fo.get('posSide')}")
        
    return results

if __name__ == "__main__":
    execute_two_sl_short()
