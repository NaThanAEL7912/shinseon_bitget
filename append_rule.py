import os

path = r'C:\Users\ClawNaEL\.gemini\AGENTS.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if '10.' not in content:
    content += '\n10. 에이전트 절대 임의 수정 금지: 어떠한 경우에도 (버그 수정이나 긴급 에러 처리를 포함하여) 기획서 승인과 폐하의 "고고" 어명 없이는 에이전트가 마음대로 코드를 수정하거나 개발을 진행하지 않는다.\n'
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Rule 10 added successfully.')
else:
    print('Rule 10 already exists.')
