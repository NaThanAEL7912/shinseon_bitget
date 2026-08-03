# 신선 비트겟 유지보수 기획서

## 1. 개요
* **목적**: 봇 내부의 자동 업데이트 모듈(`shinseon_updater.py`)이 참조하는 원격 깃허브 저장소 주소를 신규 저장소(`shinseon_bitget`)로 마이그레이션
* **상태**: [x] 개발 완료

## 2. 작업 계획
1. `shinseon_updater.py` 파일을 분석하여 하드코딩된 깃허브 API 엔드포인트를 식별한다.
2. `NaThanAEL7912/shinseon` 으로 설정된 경로를 `NaThanAEL7912/shinseon_bitget` 으로 변경한다.
   - 22라인 주변: `https://api.github.com/repos/NaThanAEL7912/shinseon_bitget/commits/master` (또는 main)
   - 104라인 주변: `https://github.com/NaThanAEL7912/shinseon_bitget/archive/refs/heads/master.zip` (또는 main)
3. 깃허브의 기본 브랜치가 `main`으로 변경되었으므로, URL의 branch 경로도 `main`으로 치환한다.
4. 수정된 내역을 로컬 깃허브 저장소에 커밋 및 원격 `main` 브랜치에 푸시한다.

## 3. 검증 계획
* 수정 후 쫄다구 코더가 올바르게 문자열 치환을 완료했는지 코드 라인을 검수한다.
* `git status`로 변경 사항을 확인하고 업로드를 수행한다.
