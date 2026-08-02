# 신선 비트겟 유지보수 및 버그 픽스 기획서

## 1. 개요
* **목적**: 마스터 앱 내 '수동 포지션 동기화'(`btn_position_sync`) 버튼 클릭 시 발생하는 구버전 Playwright(RPA) 잔재 에러(`NotImplementedError`) 해결
* **상태**: [x] 개발 완료 (수동 포지션 동기화 CCXT 통신 교체 완수)

## 2. 현상 및 원인 분석
* **현상**: 폐하께서 봇 UI의 '포지션 동기화' 버튼을 누르셨으나, 봇이 `[동기화 실패] 포지션 스캔 중 오류 발생: Playwright removed for Bitget migration` 에러를 뿜으며 뻗어버림.
* **원인**: 직전 패치(기획서 12)에서 '잔고 동기화'(`btn_sync_balance`) 버튼만 수술하고, 바로 옆에 있는 '포지션 동기화'(`btn_position_sync` -> `do_position_sync()`) 함수 내부의 거대한 Playwright 크롤링 코드를 미처 CCXT API로 교체하지 못한 소신의 뼈아픈 실책.

## 3. 작업 계획 (수술 방안)
1. `shinseon_master_app.pyw` 파일의 `do_position_sync` 비동기 함수 내부 전체(약 200줄)를 도려냄.
2. 기존 크롬 브라우저(CDP) 강제 연결 및 Vue DOM 파싱, fetch API 해킹 로직을 **전면 폐기**.
3. 글로벌 CCXT 객체(`self.bot_core.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])`)를 직접 호출하는 초광속 직통 코드로 1:1 대체.
4. 동기화 성공 시 가드레일 루프 재기상 등 기존 내부 상태값(engine flags) 업데이트 로직은 100% 보존.

## 4. 검증 계획
* 코드 수정 후 해당 버튼을 클릭하였을 때 에러 없이 즉각적으로 `✔ [동기화 완료] 열려있는 포지션이 없습니다. (100% 현금)` 또는 실제 포지션 내역을 출력하는지 확인.
