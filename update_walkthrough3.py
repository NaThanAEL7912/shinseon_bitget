import os

path = r'C:\Users\ClawNaEL\.gemini\antigravity\brain\ee372d50-927a-4c14-aa25-d1f50464ecf7\walkthrough.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = """
# 신선 봇 (SHINSEON) AWS 서버 부활 및 동기화 고도화 완수 보고

## 1. 달성한 작업
* **[기획서_8] AWS 서버 필수 라이브러리 설치**
  * 비트겟 CCXT 통신에 필요한 필수 부품(iohttp, ccxt 등)을 AWS 릴레이 서버에 설치 완료하였습니다.
* **[기획서_9] AWS 서버 부팅 크래시 버그 수정**
  * 서버 코드(shinseon_server.py) 66번째 줄의 치명적인 변수명 오타를 완벽하게 수정하였습니다.
  * 수정된 코드를 AWS 서버에 원격으로 주입하고 서버를 재부팅시켰습니다.
  * 소스코드 버전(V4.21)으로 깃허브 배포를 완료하였습니다.

## 2. 검증 결과
- 현재 AWS 릴레이 서버 후문(SSH)으로 로그를 실시간 확인한 결과, 서버가 완벽하게 부활하여 [UI] 100% 현금 대기 중 (저격 대기) 상태를 정상적으로 띄우며 대기하고 있습니다!
- 폐하의 클라이언트(V4.19 이상)에서 주기적으로 연결 재시도를 하고 있었다면, 3초 뒤에 즉각 **"서버와 웹소켓 연결 성공"**이 뜰 것입니다.

## 3. 폐하께서 확인하실 액션
- 만약 클라이언트가 계속 연결 거부 상태라면, 뷰어 앱을 **재시작**해 주시옵소서!
- 재시작 후 우측 상단의 [실전 계좌 잔고 동기화] 버튼을 누르시면, 방금 부활한 AWS 서버가 즉각 비트겟 API를 찔러서 현재 실전 잔고(USDT)를 대시보드에 뿌려줄 것입니다!
"""

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content.strip())
print('Walkthrough updated.')
