import os

path = 'docs/task.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content += '''
- [/] [기획서_7] 라이선스 서버 파일(license.json) 복구
  - [ ] docs/license.json 파일 생성 ('나엘로_노트북' 기기 등록)
  - [ ] GitHub 배포 (V4.20)
'''
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Task file updated.')
