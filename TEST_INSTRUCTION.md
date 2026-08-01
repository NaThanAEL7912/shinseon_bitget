# 신선 비트겟 (ShinSeon_Bitget) 테스트 지시서 (Phase 2 - 최종 엔진 검수)

**수신**: 세종 (QA 최고 책임자)
**발신**: 안티그래비티 (PM)

## 테스트 개요
쫄다구 코더가 BBITGET 주문 로직을 모두 적출하고, `ccxt.bitget`을 활용한 **실전 퀀트 엔진 이식(Phase 2)**을 완벽히 끝마쳤다. 
이제 봇의 핵심 체결 기능이 정상 작동하는지 논리적 무결성을 최종 검증한다.

## 테스트 수행 지침
1. **코드 정합성 분석**: `shinseon_master_app.pyw` 내부의 `_execute_bitget_internal_packet_impl` (또는 해당 체결 함수)를 눈으로 스캔하여, Playwright 관련 코드가 100% 제거되었는지 최종 확인하라.
2. **논블로킹 및 예외 처리 검증**: `asyncio.create_task`를 통해 주문이 던져지는지(Fire-and-forget), 그리고 `ccxt.NetworkError`, `ccxt.InsufficientFunds` 등에 대한 `try...except` 방어막이 제대로 설계되어 있는지 확인하라.
3. **가드레일 보존 확인**: 기존 퀀트 로직인 세션별 임계값(Current Session Threshold) 계산부나 분할 진입 변수들이 삭제되지 않고 안전하게 보존되었는지 확인하라.

## 보고 지침
위 항목들을 모두 검토한 후, 텔레그램을 통해 폐하께 **사극 톤**으로 "2차 엔진 수술(Phase 2) 코드를 전면 감찰하였사옵니다. 결과는 ..." 라고 최종 보고를 올리도록 하라. 완벽히 통과되었다면, 곧이어 깃허브 백업 및 버전업을 진행할 수 있도록 보고의 끝에 덧붙여라.
