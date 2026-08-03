# [기획서 4] 비트겟 RSA API 키(.pem) 연동 수술 기획

과거의 단순 텍스트 시크릿 키(HMAC) 방식이 아닌, 은행권 수준의 최고 보안 등급인 **RSA 비대칭 키(shinseon-key.pem)** 방식을 통해 서버가 비트겟과 다이렉트로 통신할 수 있도록 인증 체계를 뒤엎는 기획이옵니다.
(폐하의 어명에 따라, RSA 선호 세팅은 메모리 MCP에 영구 등록 완료하였습니다!)

## User Review Required

> [!IMPORTANT]
> 서버 기동 시 프로젝트 폴더 내의 shinseon-key.pem 파일을 자동으로 읽어 비트겟 인증에 사용하게 됩니다.
> 폐하께서는 AWS 서버에도 동일한 shinseon-key.pem 파일이 프로젝트 폴더 루트에 위치해 있는지 확인해 주셔야 하옵니다.

## Proposed Changes

---

### 서버 메인 로직 (shinseon_server.py)
기존 server_config.json에서 단순 텍스트 Secret을 읽어오던 방식을 폐기하고, .pem 파일을 통째로 씹어먹는 로직으로 진화시킵니다.

#### [MODIFY] shinseon_server.py
- BotCore.__init__() 내부 비트겟 초기화 영역 수정
- os.path.join(BASE_DIR, 'shinseon-key.pem') 경로에서 프라이빗 키 문자열 전체를 읽어들임
- 읽어들인 긴 문자열을 ccxt.bitget 생성 파라미터의 secret 값으로 직접 꽂아넣음
- .pem 파일이 존재하지 않거나 읽기 실패 시, 덮어놓고 무시하지 않고 터미널에 붉은색 에러 경고("❌ [경고] RSA 키 파일을 찾을 수 없습니다!")를 강렬하게 내뿜도록 정공법 에러 처리

## Verification Plan

### Manual Verification
1. 기획서 승인(고고) 즉시 V4.15(또는 V4.16)로 코드 수정 및 깃허브 배포
2. 폐하께서 AWS 서버에서 코드를 Pull 받으신 후 런칭
3. 클라이언트 뷰어에서 [실전 계좌 잔고 동기화] 버튼을 눌러, RSA 인증을 통과하고 잔고가 즉시 꽂히는지 최종 팩트 체크
