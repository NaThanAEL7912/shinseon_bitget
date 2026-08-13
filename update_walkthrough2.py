import os

path = r'C:\Users\ClawNaEL\.gemini\antigravity\brain\ee372d50-927a-4c14-aa25-d1f50464ecf7\walkthrough.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = """
# 신선 봇 (SHINSEON) 라이선스 복구 및 최종 완성 보고

## 1. 달성한 작업
* **[기획서_7] 라이선스 서버 파일(license.json) 복구 완료**
  * 저장소 이전 시 누락되었던 license.json 파일을 폐하의 옥체(노트북) 인증 정보에 맞춰 새로 생성하였습니다.
  * 기기 이름: 나엘로_노트북
  * 기기 UUID: MAC-34:6F:24:2B:A0:CE
  * 권한: MASTER (ACTIVE)
* 해당 파일을 깃허브 메인 저장소(shinseon_bitget)에 V4.20 버전으로 배포 완료하였습니다.

## 2. 검증 플랜
- 이제 깃허브 온라인 저장소에 완벽한 인증 파일이 적재되었습니다. (반영에 1~2초 정도 소요될 수 있습니다.)
- 폐하의 로컬 PC에서 뷰어를 **다시 켜시면**, 404 차단창이 완벽하게 사라지고 로그 화면에 [인증 완료] 정식 라이선스가 확인되었습니다. (소유자: 나엘로_노트북) 라는 문구와 함께 마스터 권한으로 로그인 될 것입니다!
"""

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content.strip())
print('Walkthrough updated.')
