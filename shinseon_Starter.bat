@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================================
echo  [SHINSEON] 신선 봇 및 크롬 자동 실행기
echo ====================================================
echo.
echo  1. 기존 파이썬 봇 인스턴스 정화 중...
powershell -Command "Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*shinseon*'} | Invoke-CimMethod -MethodName Terminate" >nul 2>&1

echo  2. Bitget 모니터링 크롬 브라우저 팝업 준비 중...
set "CHROME_PATH="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else (
    if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
        set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ) else (
        if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
            set "CHROME_PATH=%LocalAppData%\Google\Chrome\Application\chrome.exe"
        )
    )
)

if "%CHROME_PATH%"=="" (
    echo.
    echo ====================================================
    echo  [에러] Google Chrome 브라우저를 찾을 수 없사옵니다!
    echo  이 봇은 Google Chrome 브라우저를 기반으로 작동하오니,
    echo  아래 공식 사이트에서 크롬을 무료로 설치하신 후 다시 실행해 주시옵소서.
    echo  다운로드 링크: https://www.google.com/chrome/
    echo ====================================================
    echo.
    pause
    exit
)

netstat -ano | findstr 9224 >nul 2>&1
if %errorlevel% neq 0 (
    echo  [안내] 9224포트 모니터링 크롬을 가동합니다...
    start "Bitget_Chrome" "%CHROME_PATH%" --remote-debugging-port=9224 --user-data-dir="%~dp0ChromeDebugProfile" https://www.bitget.com/futures/usdt/BTCUSDT
    ping 127.0.0.1 -n 2 >nul
) else (
    echo  [안내] 9224포트 모니터링 크롬이 이미 가동 중입니다. (로그인 세션 보존)
)

echo  3. 신선 마스터 대시보드 구동 중...
python shinseon_updater.py --no-start
if %errorlevel% neq 0 (
    echo.
    echo ====================================================
    echo  [오류] 업데이트 검증 또는 봇 실행 실패!
    echo  위의 에러 메시지를 확인하시거나
    echo  'install.bat'을 실행하여 패키지를 다시 설치해 보십시오.
    echo ====================================================
    echo.
    pause
) else (
    start "" pythonw shinseon_master_app.pyw
)
exit
