import os

path = 'docs/기획서_7_라이선스_파일_재생성.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('"KING_CLAWNAEL"', '"나엘로_노트북"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Plan 7 updated.')
