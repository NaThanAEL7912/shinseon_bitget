# [기획서 3] 서버 API 키 세팅 및 권한 부여 기획

서버(shinseon_server.py)가 비트겟 거래소에 다이렉트로 접속하여 잔고, 포지션, 주문 내역 등을 조회할 수 있도록 서버 쪽에 비트겟 API Key를 직접 세팅하는 기획이옵니다. 
(과거 클라이언트-브라우저 모드에서는 클라이언트에만 API 키가 있었으나, 이제 통신 주체가 서버로 넘어왔기 때문에 발생하는 인증 오류를 정공법으로 해결합니다.)

## User Review Required

> [!IMPORTANT]
> 서버 설정 파일(server_config.json)에 비트겟 API 키, 시크릿, 패스워드가 추가됩니다.
> 폐하께서는 배포 완료 후, AWS 서버의 server_config.json 파일을 열어 실제 API 키 정보를 기입해 주셔야 잔고 동기화가 정상 작동하게 됩니다.

## Proposed Changes

---

### 서버 설정 파일 (server_config.json)
서버가 읽어들일 수 있도록 빈 API 키 껍데기 필드를 추가합니다.

#### [MODIFY] server_config.json
- "bitget_api_key": ""
- "bitget_api_secret": ""
- "bitget_api_password": ""

---

### 서버 메인 로직 (shinseon_server.py)
서버가 켜질 때 설정 파일에서 API 키를 읽어 ccxt 거래소 객체에 인증 정보를 먹이는 로직을 추가합니다.

#### [MODIFY] shinseon_server.py
- BotCore.__init__() 등 거래소 객체 초기화 부분 수정
- server_config.json에서 읽어온 API 키 3종 세트를 ccxt.bitget 인스턴스 생성 시 piKey, secret, password 파라미터로 주입하도록 변경
- 만약 API 키가 비어있다면, 에러 로그를 명확하게 터미널에 뿌려 폐하께서 키 입력을 누락하셨음을 직관적으로 알 수 있게(정공법) 처리

## Verification Plan

### Manual Verification
1. 기획서 승인(고고) 시 V4.15로 코드 반영 및 깃허브 배포
2. 폐하께서 AWS 서버에서 코드를 최신화(Pull) 하신 뒤, server_config.json 파일에 본인의 비트겟 API 키 입력
3. 뷰어(클라이언트)에서 [실전 계좌 잔고 동기화] 버튼을 클릭하여, 2만 불이었던 가짜 잔고가 비트겟 실제 잔고로 시원하게 바뀌는지 팩트 체크
