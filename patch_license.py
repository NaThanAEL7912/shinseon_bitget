import os

path = 'shinseon_client.pyw'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace lines 1711 to 1727 (0-indexed) with a dummy log
new_lines = lines[:1711] + ['        self.add_log("✅ [프리패스] 마스터 권한으로 라이선스 체크를 우회합니다.")\n'] + lines[1728:]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('License check removed successfully.')
