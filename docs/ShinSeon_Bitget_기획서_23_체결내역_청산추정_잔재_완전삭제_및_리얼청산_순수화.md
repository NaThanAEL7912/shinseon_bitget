# [기획서 23] 체결 내역(aggTrade) 청산 추정 잔재 완전 삭제 및 100% 찐청산(forceOrder) 순수화 (V4.28)

## 1. 개요 및 분석
- **폐하의 지시 내용:**
  "지금 바이낸스 1분 청산 신호 받고 있는 거 아니야? 저번에 아예 체결 내역은 버리지 않았나? 일본 웹서버 세팅하면서 웹소켓으로 바로 누적 청산 데이터 가져오니까 이제 체결 내역으로 유추한 청산 부분은 삭제 한 걸로 알고 있는데"
- **코드 정밀 점검 결과:**
  - 폐하의 말씀이 100% 정합하옵니다!
  - AWS 클라우드 서버 환경에서는 `run_liquidation_wss()`를 통해 바이낸스 선물 공식 실시간 청산 스트림(`wss://fstream.binance.com/ws/btcusdt@forceOrder`)이 끊김 없이 100% 직통으로 수신되고 있습니다.
  - 그러나 `shinseon_server.py` 내부의 `aggTrade` (현물/선물 체결 내역) 수신부(라인 781~788)에 과거 차단 우회 시절 잔재였던 **"$5,000 이상 체결 내역을 청산 버퍼(`liq_buffer`)에 병합 추정하는 잔재 코드"**가 여전히 남아있었습니다.
  - 이로 인해 실시간 청산 누적금(`liq_10s`) 연산 시, 바이낸스 진짜 선물 찐청산(`forceOrder`) 외에 일반 대량 체결 내역 데이터까지 청산금에 합산되는 오작동이 발생하고 있었습니다.

---

## 2. 상세 수정 및 개선 계획

###가. 체결 내역(aggTrade) 청산 버퍼 합산 잔재 코드 완전 삭제 (`shinseon_server.py`)
1. `aggTrade` 수신 이벤트 처리 루틴에서 `usd_val >= 5000.0` 시 `self.liq_buffer.append((now_t, usd_val))`를 실행하던 잔재 구문(라인 781~788)을 **완전 삭제**.
2. `aggTrade` 스트림은 오직 순수 차트 체결가/볼륨 연산(`agg_buy_vol`, `agg_sell_vol`)에만 사용하도록 격리.
3. 청산 버퍼(`liq_buffer`, `buy_liq_buffer`, `sell_liq_buffer`)는 오직 바이낸스 선물 공식 청산 스트림(`wss://fstream.binance.com/ws/btcusdt@forceOrder`)에서 발생한 **100% 리얼 찐청산(forceOrder) 이벤트 데이터만 100% 순수하게 수집 및 누적 연산**하도록 교정.

###나. 클라이언트 및 버전을 V4.28로 적용 (`shinseon_client.pyw`, `shinseon_config.json`)
1. 버전 번호를 `V4.28`로 상향 지정.
2. 클라이언트 대시보드 오더플로우 레이더에 표출되는 청산 수치가 100% 바이낸스 선물 실물 forceOrder 찐청산 데이터만 수집/연산되어 표출됨을 확인.

###다. 배포 및 검증
1. `deploy.py V4.28`을 실행하여 로컬/서버 코드 버전 업 및 GitHub main push.
2. `shinseon_server.py`를 AWS 서버(`13.192.187.244`)로 업로드(SCP).
3. AWS 서버 재가동 및 `server.log`에서 `forceOrder` 리얼 찐청산 패킷 처리 정상 가동 검증.

---

## 3. 진행 상황 및 상태
- [x] 기획서 검토 및 폐하 승인 ("고고" 어명 받음)
- [x] 쫄다구 코더 에이전트 가동 및 코드 수정
- [x] V4.28 GitHub Push & AWS 서버 적용
- [x] 개발 완료 및 검증 완수
