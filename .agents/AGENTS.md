# 신선 비트겟(ShinSeon_Bitget) 단독 개발 규칙 (AGENTS.md)

이 규칙은 `C:\Working\AntiGravity\ShinSeon_Bitget` 워크스페이스 내에서 작업을 수행할 때 소신(AI 에이전트)이 영구적으로 준수해야 하는 프로젝트 전용 지침서이옵니다.

## 1. 버전 및 업데이트 정합성 유지

* **+0.01 순차 버전업 철칙**: 향후 새로운 기능 추가나 로직 수정 시 버전을 +0.01씩 정갈하게 순차 상향(v4.01 -> v4.02 -> v4.03 ...)하여 올리옵니다.
* **버전 삼위일체 동기화**: 버전을 올릴 때에는 아래 파일들의 버전을 100% 동일하게 갱신해야 하옵니다.
  1. `shinseon_client.pyw` 내 `self.CURRENT_VERSION`
  2. `shinseon_config.json` 내 `"CURRENT_VERSION"`
  3. `docs/shinseon_whitepaper.html` 내 백서 마스터 버전
* **원격 수송 경로 준수**: 업데이트 수송기(`shinseon_updater.py`)가 최상위 루트의 파일들을 바라보므로, 원격 릴리즈 시 반드시 최상위 루트의 소스코드를 그대로 push해야 하옵니다.

## 2. 백서(Whitepaper) 동기화 의무

* **HTML 백서 업데이트**: 봇의 새로운 기능이 추가되거나 기존 기능 로직이 수정될 경우, 소신(AI)은 반드시 `docs/shinseon_whitepaper.html` (메인 백서 파일)을 최신화하여 변경된 로직을 문서에 영구 보존해야 하옵니다.

## 3. Git 자동 백업 마감 의무

* **버전 이력 로컬 및 GitHub 백업**: 개발 완료 및 검수 통과 시 소신(AI)이 `deploy.py` 또는 `git add .`, `git commit`, `git push`를 실행하여 버전 이력을 로컬 및 GitHub main 브랜치에 백업해야 하옵니다.
