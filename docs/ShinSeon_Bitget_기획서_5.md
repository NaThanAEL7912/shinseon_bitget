# 신선 비트겟 (ShinSeon_Bitget) 프로젝트 기획서 5 - 기존 시스템 분석 보고서

폐하의 어명에 따라 `C:\Working\SHINSEON` 디렉토리의 기존 '신선(ShinSeon)' 프로젝트 코드를 깊이 있게 분석한 보고서이옵니다. 본 분석을 바탕으로 비트겟(Bitget) 마이그레이션 방향을 확립할 수 있사옵니다.

## 1. 기존 시스템(BBITGET 버전) 아키텍처 및 기술 스택
* **UI 프레임워크**: `PySide6` (Qt 기반 데스크탑 앱)
* **비동기 처리**: `qasync` (PyQt와 asyncio 통합)
* **데이터 수집**: `ccxt` (바이낸스 선물 API 연동)
* **주문 실행 (BBITGET)**: `playwright` (BBITGET의 경우 정식 API가 부족하여 브라우저 자동화/스니핑 방식을 병행한 것으로 보임. `bitget_Sniffer_Launcher.bat` 존재)

## 2. 핵심 클래스 및 모듈 구조 (`shinseon_master_app.pyw`)
프로젝트는 크게 3가지 계층으로 분리되어 아주 탄탄하게 설계되어 있사옵니다.
1. **`ShinseonDashboard`**: 전체 UI 레이아웃, 차트(`pyqtgraph`), 설정 다이얼로그 관리.
2. **`BotCore`**: 백그라운드 데몬, 설정(`shinseon_config.json`) 저장/로드, 텔레그램 연동(`send_telegram_notification`) 관리.
3. **`ShinseonV35Engine`**: 핵심 트레이딩 로직을 담당하는 심장부.
   - `run_liquidation_wss`: 바이낸스 청산 맵(Websocket) 데이터 수집
   - `run_oi_polling`: 미결제약정(OI) 폴링 수집
   - `check_radar_signal_dynamic`: 조건(청산+OI) 만족 시 진입 시그널 포착
   - `execute_bitget_internal_packet`: BBITGET 거래소로 실제 주문 발송

## 3. 핵심 트레이딩 로직 (Config 기반 분석)
`shinseon_config.json`을 분석한 결과, 신선은 **매우 정교한 세션 베이스 스캘핑/모멘텀 봇**이옵니다.
* **분할 진입 (Split Entry)**: 물타기(DCA) 비율이 세팅되어 있음 (`split_entry_1_ratio`, `split_entry_2_ratio`, `split_entry_2_trigger_pct`=-0.3%).
* **세션별 가드레일 (Session Thresholds)**: 아시아, 런던(유럽), 뉴욕(US), 태평양 등 시간대별로 청산(liq), 미결제약정(oi), 손절(sl) 기준을 다르게 적용.
* **리스크 관리**: 반익절(`half_exit_enabled`), 본절 가드레일(`session_guardrails`), 쿨다운(진입 후 대기 시간) 등 프로페셔널한 자금 관리 로직 탑재.

## 4. 비트겟(Bitget) 마이그레이션 전략 (인사이트)
* **Playwright 탈피 (속도/안정성 극대화)**: 비트겟은 `ccxt`를 통한 정식 API 지원이 매우 완벽합니다. 따라서 기존 BBITGET처럼 브라우저 자동화(Playwright)를 할 필요 없이 **100% REST/Websocket API로 주문을 처리**할 수 있어 체결 속도와 봇의 안정성이 비약적으로 상승할 것입니다.
* **핵심 엔진 보존**: `ShinseonV35Engine`의 시그널 포착 로직과 분할 진입/가드레일 알고리즘은 훌륭하므로 그대로 유지하되, `execute_bitget...` 관련 함수들만 `execute_bitget...` API 호출 함수로 교체(Refactoring)하면 됩니다.

## 5. 다음 단계 (To-Do)
- [ ] 신선 비트겟 마스터 가이드 (`PROJECT_CONTEXT.md`) 작성 완료
- [ ] 안티그래비티 ↔ 세종(OpenClaw) 업무 협업 파이프라인 가동
- [ ] 비트겟 주문 모듈(Bitget API 연동) 프로토타입 작성 시작
