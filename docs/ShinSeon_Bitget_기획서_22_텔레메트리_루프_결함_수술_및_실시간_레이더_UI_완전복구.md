# [기획서 22] AWS 서버 텔레메트리 보정 루프 예외 수술 및 오더플로우 레이더 실시간 연동 완전 복구 (V4.27)

## 1. 개요 및 장애 현상 분석
- **현상:**
  1. 클라이언트 우측 오더플로우 레이더가 `● 바이낸스 1분 청산 (로딩 중)` 상태에서 갱신되지 않음.
  2. `1분 누적 청산: $0 / $2,000,000`, `1분 OI 속도: +0.000%`, `패킷 레이턴시: 0.0ms` 등 실시간 수치가 모두 초기값(0 또는 로딩 중)으로 고정됨.
- **근본 원인 (AWS 서버 로그 정밀 분석 결과):**
  - AWS 서버(`shinseon_server.py`)의 0.1초 텔레메트리 루프(`run_telemetry_loop`) 내부에서 `ShinseonV35Engine` 객체의 `entry_direction` 속성 참조 실패 예외 발생:
    `ERROR:ShinseonBot:텔레메트리 보정 루프 에러: 'ShinseonV35Engine' object has no attribute 'entry_direction'`
  - 이 예외가 0.1초마다 계속 발생하면서 `ui_callback()` (웹소켓 `ui_update` 패킷 발송) 코드가 실행되지 못하고 차단됨.
  - 서버에서 `ui_update` 패킷을 클라이언트로 송신하지 못하여 클라이언트 UI의 레이더 수치(`liq_10s`, `oi_speed`, `ping_ms`, `current_session`, `target_liq` 등)가 갱신되지 않고 멈춰 있었음.

---

## 2. 상세 수정 및 보완 계획

###가. AWS 서버 텔레메트리 루프 및 포지션 동기화 보강 (`shinseon_server.py`)
1. **`ShinseonV35Engine.__init__` 기본 속성 선언 보강:**
   - `self.entry_direction = "LONG"` 및 `self.position_side = "LONG"` 속성을 클래스 초기화 시 명시적으로 선언하여 속성 부재 예외 완전 방지.
2. **`run_telemetry_loop` 예외 방어 가드 강화:**
   - `direction_active` 추출 시 `getattr(self.v35_engine, "entry_direction", None) or getattr(self.v35_engine, "position_side", "LONG") or "LONG"` 구문으로 이중 안전 장치 적용.
3. **`CMD_SYNC_POSITION` 핸들러 속성 동기화 완벽화:**
   - 포지션 조회 시 `self.v35_engine.entry_direction = side` 및 `self.v35_engine.position_side = side`를 둘 다 동기화 설정.

###나. 클라이언트 오더플로우 레이더 연동 보강 (`shinseon_client.pyw`)
1. **`CURRENT_VERSION`을 `V4.27`로 버전 업.**
2. **레이더 수치 실시간 갱신 수용 검증:**
   - 서버에서 정상 송신되는 `ui_update` 패킷을 받아 `bar_liq`, `bar_oi`, `lbl_ping_ms`, `lbl_radar_title` 세션 정보가 0.1초 단위로 실시간 무결하게 업데이트되도록 확인.

###다. 배포 및 검증
1. `deploy.py V4.27`을 실행하여 로컬/서버 코드 버전 업 및 GitHub main 브랜치 push.
2. `shinseon_server.py`를 AWS 서버(`13.192.187.244`)로 재업로드(SCP).
3. AWS 서버 재가동 (`fuser -k 8765/tcp; nohup python3 -u /home/ubuntu/shinseon_server.py > /home/ubuntu/server.log 2>&1 &`).
4. AWS `server.log`에서 `텔레메트리 보정 루프 에러` 완전 소멸 확인 및 클라이언트 레이더 수치 실시간 연동 최종 검증.

---

## 3. 진행 상황 및 상태
- [x] 기획서 검토 및 폐하 승인 ("고고" 어명 완료)
- [x] 쫄다구 코더 에이전트 가동 및 코드 수정
- [x] V4.27 GitHub Push & AWS 서버 적용
- [x] 개발 완료 검증 및 문서 업데이트 (개발 완료)
