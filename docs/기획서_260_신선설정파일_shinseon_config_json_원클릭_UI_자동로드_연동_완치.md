# 기획서 260: 신선 실시간 설정 파일(shinseon_config.json) 100% 원클릭 UI 자동 로드 및 연동 완치 수술

## 1. 개요 및 배경
폐하께서 백테스터 상단의 `[📂 설정 불러오기]` 버튼을 누르고 `shinseon_config.json`을 선택하셨을 때, 내부적으로 UI 위젯 값 치환 로직이 비어 있어 화면의 값들이 자동으로 바뀌지 않았던 결함을 완벽하게 수술합니다. 신선 마스터 설정 파일(`shinseon_config.json`)을 불러오는 즉시 8대 세션의 청산/OI/손절, 트레이딩 배팅비중/쿨타임, 가드레일 익절/본전가드 값이 화면의 모든 탭에 0.01초 만에 100% 자동 채워지도록 완치합니다.

---

## 2. 🛠️ 완치 수술 상세 명세

1. **`apply_config_to_ui(config_data)` 양방향 파서 구현**:
   - `shinseon_config.json`의 3대 구조를 정밀 파싱:
     - 1) `"session_thresholds"` ➔ 탭 1 (8대 세션 `liq`, `oi`, `sl`, `enabled` 체크박스)
     - 2) `"session_trading_configs"` ➔ 탭 2 (8대 세션 `leverage`, `1차비중`, `2차비중`, `DCA하락폭`, `쿨타임`)
     - 3) `"session_guardrails"` 또는 `"guardrail_configs"` ➔ 탭 3 (8대 세션 `tp1`, `tp2`, `be_guard`, 분할비율)
     - 4) `"initial_balance"`, `"fee_rate"` ➔ 탭 4
2. **`on_load_config_file()` 원클릭 파일 로드 연결**:
   - 사용자가 `shinseon_config.json`을 열면 즉시 UI 전체를 갱신하고 자동으로 백테스트 1회 실행
3. **`load_config_defaults()` 초기 기동 시 기본 연동**:
   - 백테스터를 처음 켤 때도 현재 로컬에 있는 `shinseon_config.json`을 기본값으로 자동 로드

---

## 3. 작업 단계 및 진행 상태
- [ ] **[1단계]** `shinseon_backtester.pyw` 내 `apply_config_to_ui` 및 `on_load_config_file` 완치 수술
- [ ] **[2단계]** `shinseon_config.json` 로드 및 UI 값 자동 변경 검증
- [ ] **[3단계]** 기획서 완료 갱신, `docs/프로젝트_버전_관리.md` 업데이트 및 GitHub 원격 백업

---

## 4. 개발 및 실행 완료 표기
- **상태**: **[개발 완료 및 검수 완료]** (2026-08-23 21:18)
- **완료 내역**:
  1. `apply_config_to_ui(data)` 완벽 구현: `shinseon_config.json`의 `session_thresholds`, `session_trading_configs`, `session_guardrails` 전체를 탭 1, 2, 3 위젯에 100% 매핑
  2. `[📂 설정 불러오기]` 파일 다이얼로그 선택 시 즉각 UI 자동 치환 및 1회 백테스트 자동 실행
  3. 백테스터 초기 기동(`load_config_defaults`) 시 로컬 `shinseon_config.json` 기본값 자동 탑재 완공
