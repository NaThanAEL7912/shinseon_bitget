# 신선 비트겟 (ShinSeon_Bitget) 프로젝트 기획서 10 - GitHub 새 저장소 분리 및 업로드 가이드

폐하, 기존 BBITGET용 프로그램과 소스코드가 섞이는 것을 막기 위해 **완전히 새로운 GitHub 저장소(Repository)**로 분리하는 것은 매우 훌륭한 결단이시옵니다! 

소신이 현재 작업 폴더(`C:\Working\AntiGravity\ShinSeon_Bitget`)에 독립적인 로컬 Git 저장소를 생성하고, 방금 전 1차 뼈대 공사 내역까지 모두 안전하게 `commit` (포장) 해두었사옵니다.

이제 폐하께서 직접 GitHub에 새 저장소를 파시고, 이 포장된 코드를 쏘아 올리시기만 하면 되옵니다.

## GitHub 새 저장소 연결 및 업로드 방법

**1. GitHub 웹사이트에서 새 저장소 만들기**
- GitHub.com에 로그인하시어 우측 상단의 `+` 버튼 -> **New repository**를 클릭하옵소서.
- Repository name 칸에 `ShinSeon_Bitget` 이라고 적어 주시옵소서.
- 기존처럼 프라이빗하게 쓰시려면 **Private**을 선택하시고, 맨 아래 **Create repository** 초록색 버튼을 꽉 눌러주시옵소서. (※ 주의: README, .gitignore 등은 절대 추가하지 마옵소서! 빈 깡통이어야 하옵니다.)

**2. 생성된 주소(URL) 복사하기**
- 방금 만들어진 빈 깡통 저장소 화면에서 `https://github.com/폐하의아이디/ShinSeon_Bitget.git` 형태의 주소를 복사(Copy)해 주시옵소서.

**3. 로컬 폴더에서 터미널 열고 명령어 입력**
- `C:\Working\AntiGravity\ShinSeon_Bitget` 폴더에서 명령 프롬프트(CMD)나 PowerShell을 여시고 아래 명령어를 한 줄씩 복사해서 엔터를 쳐주시옵소서.

```bash
# 1. 새 깃허브 주소를 'origin'이라는 이름으로 연결합니다.
# (아래 주소 부분은 폐하께서 복사하신 주소로 꼭 바꿔서 입력하셔야 하옵니다!)
git remote add origin https://github.com/폐하의아이디/ShinSeon_Bitget.git

# 2. 메인 나뭇가지(Branch) 이름을 main으로 확정 짓습니다.
git branch -M main

# 3. 로컬에 포장해 둔 코드를 깃허브로 쏘아 올립니다!
git push -u origin main
```

위 3줄의 어명만 터미널에 내려주시면, 기존 신선(BBITGET)과는 100% 분리된 깨끗하고 강력한 비트겟 전용 깃허브 저장소가 완벽히 구축될 것이옵니다!
