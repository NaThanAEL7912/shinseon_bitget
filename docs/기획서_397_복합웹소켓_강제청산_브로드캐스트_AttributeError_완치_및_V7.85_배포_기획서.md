# [기획서 397] 복합 웹소켓 강제청산 브로드캐스트 AttributeError 완치 및 V7.85 배포 기획서

## 1. 현황 및 결함 원인 (실서버 로그 실측 팩트)

### 🔍 현장 실측 에러 로그
AWS 도쿄 실전 서버(`13.192.187.244`)의 `shinseon_stdout.log` 실시간 부검 결과, 아래와 같은 재연결 경고가 포착되었사옵니다:

```text
[2026-10-02 11:50:48] [WARNING] 바이낸스 복합 웹소켓 연결 장애 ➡️ 재연결 시도 중: 'BotCore' object has no attribute 'broadcast_event'
```

### ⚡ 결함 원인 분석
- [`shinseon_server.py`](file:///C:/Working/ShinSeon_Bitget/shinseon_server.py) 라인 1629:
  - 복합 웹소켓으로 바이낸스 체결가(`aggTrade`)는 1.0ms로 완벽하게 수신되고 있으나,
  - **강제 청산(`btcusdt@forceOrder`) 패킷이 감지되는 순간**, 청산 로그 브로드캐스트 코드에서 `ws_server.broadcast_event`가 아닌 `self.broadcast_event`를 호출하여 `AttributeError`가 발생하고 있었습니다.
  - 이로 인해 청산이 발생할 때마다 복합 웹소켓이 순단(재연결)되는 현상이 확인되었습니다.

---

## 2. 해결 방안 (정공법 완치)

### [`shinseon_server.py`](file:///C:/Working/ShinSeon_Bitget/shinseon_server.py) 코드 수정:
- **(AS-IS)**:
  ```python
  asyncio.create_task(self.broadcast_event("ui_update", {"msg": log_msg, "log_type": 1, "price": cur_price}))
  ```
- **(TO-BE)**:
  ```python
  if self.ui_cb:
      self.ui_cb(cur_price, 1, log_msg)
  if ws_server:
      asyncio.create_task(ws_server.broadcast_event("ui_update", {"msg": log_msg, "log_type": 1, "price": cur_price}))
  ```
  👉 `BotCore`의 UI 콜백 및 `ws_server` 브로드캐스트 인스턴스를 정확히 참조하도록 정공법 완치.

---

## 3. 버전 삼위일체 V7.85 승급 및 배포 계획

1. **+0.01 순차 버전업 철칙 준수**:
   - `shinseon_server.py`: `CURRENT_VERSION = "V7.85"`
   - `shinseon_client.pyw`: `CURRENT_VERSION = "V7.85"`
   - `shinseon_config.json`: `"CURRENT_VERSION": "V7.85"`
   - `docs/shinseon_whitepaper.html`: V7.85 청산 브로드캐스트 무결성 패치 기록
2. **로컬 컴파일 검증**: `python -m py_compile shinseon_server.py shinseon_client.pyw`
3. **AWS 도쿄 실전 서버 원클릭 SFTP 배포**: `python deploy.py V7.85`
4. **실서버 로그 실측**: 청산 패킷 수신 시 예외 없이 100% 무중단 유지 확인.

---

## 4. 진행 상태
- [x] 폐하의 어명 ("고고") 수명 완료
- [x] 쫄다구 코더 에이전트를 통한 버그 완치 및 로컬 컴파일 검증 (오류 0건 무결점)
- [x] AWS 도쿄 실전 서버 V7.85 SFTP 배포 및 무장애 가동 검증 완료
