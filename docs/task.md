- [x] 서버 설정 및 API 인증 기능 개발 (shinseon_server.py)
  - [x] server_config.json 에 비트겟 API 키 필드 추가
  - [x] shinseon_server.py 에서 config 의 API 키를 읽어 ccxt.bitget 초기화에 주입
  - [x] API 키가 없을 경우 터미널에 명확한 에러 로그 출력 (정공법 원칙 준수)
- [x] 쫄다구 에이전트 작업 100% 직접 검수 (AGENTS.md 3번 룰 준수)
- [x] 배포 및 버전업 관리 문서 갱신

- [x] [기획서_6] 라이선스 에러 수정
  - [x] shinseon_client.pyw 내 LICENSE_URL 수정 (shinseon -> shinseon_bitget)
- [x] [기획서_5] 비트겟 브라우저 다이렉트 오픈 버튼 신설
  - [x] shinseon_client.pyw 내 UI 버튼 추가 (이미 적용됨)
  - [x] 버튼 클릭 시 webbrowser 모듈로 비트겟 URL 호출 기능 연동 (이미 적용됨)

- [/] [기획서_7] 라이선스 서버 파일(license.json) 복구
  - [ ] docs/license.json 파일 생성 ('나엘로_노트북' 기기 등록)
  - [ ] GitHub 배포 (V4.20)

- [/] [기획서_8] AWS 서버 패키지 설치
  - [ ] AWS 서버에 aiohttp, ccxt 등 설치
  - [ ] AWS 서버 봇 재부팅 (tmux)

- [/] [기획서_9] AWS 서버 부팅 크래시 수정
  - [ ] shinseon_server.py 오타 수정 (self.server_config -> env_vars)
  - [ ] GitHub 배포 (V4.21)
  - [ ] AWS 서버에 수정된 shinseon_server.py 업로드 (scp)
  - [ ] AWS 서버 tmux 재부팅 및 정상 동작 검증

- [/] [기획서_10] 잔고 동기화 버그 수정 및 0원 표기
  - [ ] shinseon_server.py CCXT swap 옵션 추가 및 비동기(fetch_balance) 코드 수정
  - [ ] shinseon_client.pyw 가짜 2만불 텍스트 제거 및 0.00 초기화
  - [ ] GitHub 배포 (V4.22)
  - [ ] AWS 서버에 수정된 shinseon_server.py 반영 및 tmux 재부팅
