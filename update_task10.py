import os

path = 'docs/task.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content += '''
- [/] [기획서_10] 잔고 동기화 버그 수정 및 0원 표기
  - [ ] shinseon_server.py CCXT swap 옵션 추가 및 비동기(fetch_balance) 코드 수정
  - [ ] shinseon_client.pyw 가짜 2만불 텍스트 제거 및 0.00 초기화
  - [ ] GitHub 배포 (V4.22)
  - [ ] AWS 서버에 수정된 shinseon_server.py 반영 및 tmux 재부팅
'''
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Task file updated.')
