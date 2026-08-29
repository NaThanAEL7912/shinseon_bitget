# [기획서 366] 백테스터 GUI 불필요한 OI 진입 모드 콤보박스 완전 삭제 및 UI 정문화 기획서

## 1. 개요 및 배경
- **배경**: 실전 서버(`shinseon_server.py`) 및 백테스터 코어 엔진(`backtest_engine.py`)은 신선 대헌법 V2.55에 따라 오직 **+OI (양수 자금유입 돌파)** 조건만을 단일 불변 헌법으로 채택하여 100% 디지털 트윈 일치화를 완료하였음.
- **문제점**: 백테스터 GUI(`shinseon_backtester.pyw`) 상단 헤더에 잔존하던 '🎯 OI 진입 모드' 콤보박스(🟢 +OI vs ⚪ abs(OI))는 실전 서버와 괴리를 유발할 수 있는 불필요한 레거시 UI 요소임.
- **목적**: 불필요한 OI 진입 모드 콤보박스 및 관련 엔진 파싱 코드를 완전히 제거하여 UI를 간결하고 정문화하고, 실전 서버와의 100% 일체감을 확립함.

---

## 2. 세부 작업 내역

### [1] 백테스터 GUI (`shinseon_backtester.pyw`)
- [x] 버전 헤더 V7.69 갱신 (Line 3, 201, 256)
- [x] 상단 헤더 내 `🎯 OI 진입 모드:` 라벨 및 `self.cb_oi_mode` 콤보박스 UI 생성/스타일/위젯 추가 코드 완전 삭제
- [x] `collect_ui_config()` 내 `cb_oi_mode` 파싱 코드 및 반환 딕셔너리 `'oi_direction_mode'` 키 완전 삭제
- [x] `apply_config_to_ui()` 내 `# 6. 🎯 OI 진입 모드 복원` 블록 완전 삭제

### [2] 백테스터 엔진 (`backtest_engine.py`)
- [x] 버전 헤더 V7.69 갱신 (Line 3)
- [x] `run_backtest_simulation()` 내 잔존 `oi_direction_mode` 미사용 파싱 변수 라인 완전 삭제

### [3] 버전 삼위일체 V7.69 갱신
- [x] `shinseon_server.py`: `self.CURRENT_VERSION = "V7.69"`
- [x] `shinseon_client.pyw`: `self.CURRENT_VERSION = "V7.69"`
- [x] `shinseon_config.json`: `"CURRENT_VERSION": "V7.69"`
- [x] `docs/shinseon_whitepaper.html`: V7.69 및 20260829 백서 마스터 버전 갱신

### [4] 버전 관리 및 배포
- [x] `docs/프로젝트_버전_관리.md` V7.69 이력 등재
- [x] 전체 파이썬 파일 문법 컴파일 검증 (`py_compile`)
- [x] AWS 실전 도쿄 서버 배포 (`deploy.py V7.69`) 및 데몬 무중단 가동 확인
- [x] Git 커밋 및 GitHub 원격 push 완료

---

## 3. 검증 및 완료 여부
- [x] **개발 완료**: 백테스터 GUI 상단 불필요한 OI 진입 모드 콤보박스 완전 삭제 및 V7.69 배포 완공
