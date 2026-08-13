import os

path = 'docs/task.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content += '''
- [/] [기획서_8] AWS 서버 패키지 설치
  - [ ] AWS 서버에 aiohttp, ccxt 등 설치
  - [ ] AWS 서버 봇 재부팅 (tmux)
'''
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Task file updated.')
