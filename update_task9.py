import os

path = 'docs/task.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content += '''
- [/] [기획서_9] AWS 서버 부팅 크래시 수정
  - [ ] shinseon_server.py 오타 수정 (self.server_config -> env_vars)
  - [ ] GitHub 배포 (V4.21)
  - [ ] AWS 서버에 수정된 shinseon_server.py 업로드 (scp)
  - [ ] AWS 서버 tmux 재부팅 및 정상 동작 검증
'''
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Task file updated.')
