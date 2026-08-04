# ShinSeon_Bitget 기획서 #19: AWS 웹서버 구현 현황 및 트레이딩 설정 완전 동기화 보고서

## 1. 개요
폐하의 하명에 따라 텔레그램 및 알림 사운드 설정(클라이언트 PC 전용)을 제외한 **모든 트레이딩 핵심 파라미터(세션별 임계치, 가드레일, 레버리지, 분할 배팅 비중, 쿨타임, 익절/손절 비중 등 전체)**가 AWS 웹서버 엔진으로 실시간 전송되어 서버 알고리즘에 100% 즉시 반영되도록 구현 설계를 수립함.

---

## 2. 웹서버 전송 파라미터 상세 명세 (텔레그램/사운드 제외 전체)

### [전송 대상: 트레이딩 핵심 파라미터 100%]
1. **세션별 기본 임계치 (`session_thresholds`)**
   - 아시아, 유럽, 미국 본장, 태평양 횡보, 주말 세션별 목표 청산액(`liq`), OI 속도(`oi`), 최초 손절선(`sl`), 활성화(`enabled`)
2. **세션별 가드레일 설정 (`session_guardrails`)**
   - 세션별 가드레일 발동 트리거(`trigger`), 가드 한도(`guard`), 활성화(`enabled`)
3. **레버리지 및 배팅 비중 (`leverage_level`, `betting_ratio`)**
   - 설정 레버리지(1~150배) 및 총 진입 배팅 비중(%)
4. **분할 진입 및 트리거 파라미터 (`split_entry`)**
   - 1차/2차/3차 진입 비중(`split_entry_1/2/3_ratio`), 2차/3차 진입 트리거(`split_entry_2/3_trigger_pct`), 분할진입 쿨타임(`split_cooldown_seconds`)
5. **쿨타임 파라미터 (`cooldown_seconds`)**
   - 일반 쿨타임(`cooldown_seconds`) 및 익절 후 쿨타임(`profit_cooldown_seconds`)
6. **익절 및 불타기 파라미터 (`half_exit`, `pyramiding`)**
   - 1차 반청산 비중(`half_exit_close_ratio`), 불타기 활성화(`pyramiding_enabled`), 불타기 비중(`pyramiding_ratio`)
7. **수동 임계치 오버라이드 (`manual_threshold`)**
   - 수동 임계치 사용 여부(`manual_threshold`), 수동 청산액(`target_liq`), 수동 OI속도(`target_oi`), 허용 슬리피지(`target_slippage`)

### [제외 대상: 클라이언트 전용 UI/알림 설정]
- 텔레그램 알림 설정 (`telegram_enabled`, `telegram_token`, `telegram_chat_id`)
- 알림 사운드 설정 (`sound_enabled`)

---

## 3. 정공법 동기화 수립 계획

### [클라이언트 수정: `shinseon_client.pyw`]
- 설정 창 `[적용 및 저장]` 클릭 시 및 수동 임계치 변경 시, 상기 **트레이딩 핵심 파라미터 전체**를 JSON 패킷(`CMD_UPDATE_CONFIG`)으로 포장하여 AWS 서버로 전송.
- 웹소켓 `ui_update` 패킷 수신 시, 서버의 실시간 장세(`current_session`: 예 `🟡 유럽 장세 (KST 19:40:51)`) 및 실시간 청산 목표액(`target_liq`)을 오더플로우 레이더 상단 및 게이지 바에 동적 표기.

### [서버 수정: `shinseon_server.py`]
- `CMD_UPDATE_CONFIG` 명령 수신 시, 전달받은 **트레이딩 파라미터 전체**를 서버 메모리 및 `v35_engine` 알고리즘(손절선, 레버리지, 쿨타임, 가드레일 등)에 즉시 동적 반영하고 서버 `shinseon_config.json`에 영구 보존.

---

## 4. 개발 진행 상태
- [x] 개발 완료 (V4.24 클라이언트-서버 트레이딩 파라미터 100% 완전 동기화 개발 집행 완료)
