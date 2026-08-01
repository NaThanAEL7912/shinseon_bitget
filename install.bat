@echo off
chcp 65001 >nul

echo ====================================================
echo  [SHINSEON] 파이썬 패키지 및 종속성 원클릭 설치기
echo ====================================================
echo.
echo  신선 봇 구동에 필요한 라이브러리 설치를 시작합니다.
echo.
:: 파이썬 설치 여부 확인 및 자동 설치
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ====================================================
    echo  [안내] 이 컴퓨터에 파이썬이 설치되어 있지 않습니다.
    echo  자동으로 파이썬 3.12.4 설치를 시작하옵니다...
    echo ====================================================
    echo.
    
    echo [1/3] 파이썬 설치 파일 다운로드 중 (공식 홈페이지)...
    curl -L -o python_installer.exe https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe
    if %errorlevel% neq 0 (
        echo.
        echo [에러] 파이썬 설치 파일 다운로드에 실패하였습니다!
        echo 인터넷 연결 상태를 확인하시거나 직접 파이썬을 설치해 주십시오.
        pause
        exit
    )
    
    echo [2/3] 백그라운드 조용히 설치 진행 중 (약 30초 소요)...
    python_installer.exe /quiet PrependPath=1 Include_test=0 Include_pip=1
    timeout /t 10 /nobreak >nul
    del python_installer.exe
    
    echo [3/3] 파이썬 임시 환경 변수 등록 및 즉시 갱신 중...
    :: 현재 CMD 세션에 경로 즉각 반영 (재부팅/재실행 방지)
    set "PATH=%LocalAppData%\Programs\Python\Python312\;%LocalAppData%\Programs\Python\Python312\Scripts\;%PATH%"
    set "PATH=C:\Program Files\Python312\;C:\Program Files\Python312\Scripts\;%PATH%"
    
    echo.
    echo  ✔ 파이썬 설치가 성공적으로 완료되었습니다!
    echo.
)

echo 1. pip 패키지 설치 진행 중... (requirements.txt)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo 2. Playwright 브라우저 종속성 설치 진행 중...
python -m playwright install chromium

echo.
echo ====================================================
echo  모든 종속성 라이브러리 설치가 완료되었습니다!
echo  이제 'shinseon_Starter.bat'을 실행하시면 가동됩니다.
echo ====================================================
echo.
pause
exit
