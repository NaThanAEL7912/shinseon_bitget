import json

message = '{"type": "EVT_SYNC_BALANCE", "data": {"usdt_total": 0.0}}'
data = json.loads(message)
msg_type = data.get('type')
payload = data.get('data', {})

if msg_type == 'EVT_SYNC_BALANCE':
    usdt_total = payload.get('usdt_total', 0.0)
    print(f"✅ [잔고 동기화] 실전 계좌 잔고가 업데이트되었습니다: ${usdt_total:,.2f}")
