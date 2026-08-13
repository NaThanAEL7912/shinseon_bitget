import os

path = 'docs/기획서_10_서버_잔고동기화_버그_수정.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('## 2. 해결 방안 (Proposed Changes)', '''## 2. 해결 방안 (Proposed Changes)
- **수정 대상 파일:** shinseon_server.py, shinseon_client.pyw
- **작업 내용:** 
  1. (서버) CCXT 초기화 옵션에 {'options': {'defaultType': 'swap'}} (선물 계좌 기본값) 추가.
  2. (서버) 잔고 조회 코드에서 syncio.to_thread를 벗겨내고 순수 비동기 호출(wait self.bot_core.bitget_exchange.fetch_balance())로 변경.
  3. (클라이언트) 폐하의 어명에 따라, 클라이언트 최초 실행 시 표시되던 가짜 2만불($20,000.00) 텍스트를 삭제하고, $0.00 (실시간 동기화 대기)로 표시되도록 수정. 0원이면 정직하게 0원으로 즉각 반영되도록 조치.
''')

import re
content = re.sub(r'- \*\*수정 대상 파일:\*\* shinseon_server.py\n- \*\*작업 내용:\*\* \n  1\. \(줄 72\) CCXT 초기화 옵션에 .*?\n  2\. \(줄 2013\) 잔고 조회 코드에서 .*?\n', '', content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Plan 10 updated.')
