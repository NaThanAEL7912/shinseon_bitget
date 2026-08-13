import os

path = 'docs/task.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('- [/] [기획서_6]', '- [x] [기획서_6]')
content = content.replace('- [ ] shinseon_client.pyw 내 LICENSE_URL 수정', '- [x] shinseon_client.pyw 내 LICENSE_URL 수정')
content = content.replace('- [/] [기획서_5]', '- [x] [기획서_5]')
content = content.replace('- [ ] shinseon_client.pyw 내 UI 버튼 추가', '- [x] shinseon_client.pyw 내 UI 버튼 추가 (이미 적용됨)')
content = content.replace('- [ ] 버튼 클릭 시 webbrowser 모듈로 비트겟 URL 호출 기능 연동', '- [x] 버튼 클릭 시 webbrowser 모듈로 비트겟 URL 호출 기능 연동 (이미 적용됨)')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Tasks marked as completed.')
