# ShinSeon_Bitget 기획서 #20: 비트겟 실전 포지션 실시간 동기화 구현

## 1. 개요 및 현상
- **현상**: 비트겟 거래소 웹화면에 실전 포지션(예: `BTCUSDT-Isolated-Long-10x`, 진입가 $64,601.3, 수량 0.0005 BTC)이 실제 존재함에도 불구하고, 클라이언트 대시보드에서 `[포지션 동기화]` 버튼을 누르면 잔고($34.79)만 업데이트되고 포지션 상태는 `[100% 현금 대기 중]`으로 고정되어 포지션을 동기화하지 못함.
- **원인**: AWS 서버(`shinseon_server.py`)의 `CMD_SYNC_POSITION` 핸들러가 잔고 조회(`fetch_balance`)만 수행하고, 비트겟 실제 포지션 조회 API(`fetch_positions`)를 호출하지 않아 서버 봇 엔진(`v35_engine`) 및 클라이언트 UI가 포지션을 인식하지 못함.

---

## 2. 세부 개발 및 수정 계획

### [서버 측 수정: `shinseon_server.py`]
1. **`CMD_SYNC_POSITION` 수신 시 비트겟 실물 포지션 조회 연동**
   - `self.bot_core.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])` 또는 `fetch_positions()` 호출.
   - 수량(contracts / size)이 0보다 큰 활성 포지션 추출.
2. **서버 봇 엔진 (`v35_engine`) 포지션 상태 사전 동기화**
   - 포지션 존재 시: `is_position_active = True`, 방향(`LONG`/`SHORT`), 진입가(`entry_price`), 수량(`position_volume`), 레버리지 등 동기화 세팅.
   - 포지션 미보유 시: `is_position_active = False`.
3. **클라이언트 브로드캐스트 패킷 송신 (`EVT_SYNC_POSITION`)**
   - `broadcast_event("EVT_SYNC_POSITION", {"has_position": True, "side": "LONG", "volume": 0.0005, "entry_price": 64601.3, ...})` 전송.

### [클라이언트 측 수정: `shinseon_client.pyw`]
1. **`EVT_SYNC_POSITION` 웹소켓 수신부 핸들러 신설**
   - 수신된 포지션 정보를 기반으로 대시보드 `진입/정산 상태` 라벨을 `[LONG 진입 중: 0.0005 BTC @ $64,601.3 (10x)]` 형태로 실시간 갱신 표기.

---

## 3. 개발 진행 상태
- [x] 개발 완료
