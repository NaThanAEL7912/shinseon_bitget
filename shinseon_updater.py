import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse
import py_compile
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "shinseon_config.json")
MAIN_APP_PATH = os.path.join(BASE_DIR, "shinseon_master_app.pyw")
TEMP_APP_PATH = os.path.join(BASE_DIR, "shinseon_master_app_temp.pyw")

# GitHub 원격 설정 (공개 Raw 수송 URL 및 CDN 캐시 바이패스 수송선)
DEFAULT_CONFIG_URL = "https://raw.githubusercontent.com/NaThanAEL7912/shinseon/master/shinseon_config.json"
DEFAULT_APP_URL = "https://raw.githubusercontent.com/NaThanAEL7912/shinseon/master/shinseon_master_app.pyw"

def get_latest_master_urls():
    sha = "master"
    try:
        req = urllib.request.Request("https://api.github.com/repos/NaThanAEL7912/shinseon/commits/master", headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                sha = data.get("sha", "master")
                print(f" [CDN 바이패스] 최신 master 커밋 SHA({sha[:7]}) 기반 동적 수송 URL 결합 완료")
    except Exception as e:
        print(f" [경고] GitHub API SHA 파싱 실패 ({e}), 기본 master URL을 사용합니다.")
    
    config_url = f"https://raw.githubusercontent.com/NaThanAEL7912/shinseon/{sha}/shinseon_config.json"
    app_url = f"https://raw.githubusercontent.com/NaThanAEL7912/shinseon/{sha}/shinseon_master_app.pyw"
    return config_url, app_url

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config_data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def download_file_with_token(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=15.0) as response:
        return response.read()

def is_version_newer(current_version, latest_version):
    curr = current_version.strip().lower().replace("v", "").replace("b", "")
    late = latest_version.strip().lower().replace("v", "").replace("b", "")
    curr_parts = curr.split(".")
    late_parts = late.split(".")
    
    max_len = max(len(curr_parts), len(late_parts))
    for i in range(max_len):
        curr_val = 0
        if i < len(curr_parts):
            try:
                curr_val = int(curr_parts[i])
            except ValueError:
                curr_val = 0
        late_val = 0
        if i < len(late_parts):
            try:
                late_val = int(late_parts[i])
            except ValueError:
                late_val = 0
        if late_val > curr_val:
            return True
        elif late_val < curr_val:
            return False
    return False

def get_local_version():
    if os.path.exists(MAIN_APP_PATH):
        try:
            with open(MAIN_APP_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            match = re.search(r"self\.CURRENT_VERSION\s*=\s*[\"']([^\"']+)[\"']", content)
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f" 마스터 앱 내부 버전 파싱 실패: {e}")
    
    config_data = load_config()
    return config_data.get("CURRENT_VERSION", "v1.4")

def main():
    # 콘솔 인코딩 강제 설정 (Windows CP949 오류 방지)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if sys.platform.startswith('win'):
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleCP(65001)
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
            
    print("====================================================")
    print(" [SHINSEON] GitHub 연동 실시간 업데이트 감지 엔진")
    print("====================================================")
    
    config_data = load_config()
    current_version = get_local_version()
    print(f" 현재 로컬 설치 버전: {current_version}")

    updated = False
    try:
        # 1. GitHub 원격 서버의 최신 설정 파일 조회
        print(" GitHub 배포 서버 정보 조회 중...")
        config_url, app_url = get_latest_master_urls()
        config_bytes = download_file_with_token(config_url)
        remote_config = json.loads(config_bytes.decode('utf-8'))
        
        latest_version = remote_config.get("CURRENT_VERSION", "v1.4").strip()
        print(f" 최신 가용 버전 확인: {latest_version}")

        # 버전 대조
        is_newer = is_version_newer(current_version, latest_version)

        is_force = "--force" in sys.argv

        if is_newer or is_force:
            action_name = "강제 갱신 수송" if is_force else "신규 버전 수송"
            print(f" [{action_name}] GitHub로부터 새 마스터 빌드 다운로드 시작...")
            code_bytes = download_file_with_token(app_url)

            # 2. 문법 안전 검증
            with open(TEMP_APP_PATH, "wb") as f_temp:
                f_temp.write(code_bytes)

            try:
                py_compile.compile(TEMP_APP_PATH, doraise=True)
                
                # 3. 안전 교체 (기존 실행 중인 마스터 프로세스 강제 종료하여 파일 락 해제)
                try:
                    import subprocess
                    # wmic 구버전 명령어 의존 제거 ➡️ taskkill로 pythonw.exe 100% 완벽 강제 종료
                    subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe", "/T"], creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    import time
                    time.sleep(0.5)
                except Exception:
                    pass

                if os.path.exists(MAIN_APP_PATH):
                    os.remove(MAIN_APP_PATH)
                os.rename(TEMP_APP_PATH, MAIN_APP_PATH)
                
                # 4. 버전 설정 갱신
                config_data["CURRENT_VERSION"] = latest_version
                save_config(config_data)
                print(f" [성공] {latest_version} 마스터 빌드로 자가 업데이트가 완수되었습니다!")
                updated = True
                
                print(f" [알림] 최신 마스터 빌드({latest_version}) 업데이트 완수!")
                try:
                    msg = f"신선 봇이 최신 버전({latest_version})으로 성공적으로 업데이트 완료되었습니다!"
                    ctypes.windll.user32.MessageBoxW(0, msg, "신선 업데이트 수송기", 0x40)
                except Exception:
                    pass
            except Exception as e_compile:
                print(f" [오류] 다운로드된 파일의 문법 검증이 실패하여 업데이트를 기각합니다: {e_compile}")
                if os.path.exists(TEMP_APP_PATH):
                    os.remove(TEMP_APP_PATH)
        else:
            print(f" [알림] 현재 최신 버전({latest_version})을 사용 중이옵니다. 봇을 기동합니다.")
            try:
                msg = f"현재 최신 버전({latest_version})을 사용 중이옵니다. 봇을 기동하겠나이다."
                ctypes.windll.user32.MessageBoxW(0, msg, "신선 업데이트 수송기", 0x40)
            except Exception:
                pass

    except Exception as e:
        print(f" [오류] 업데이트 동기화 중 에러가 발생했습니다: {e}")

    # 프로그램 실행 흐름 유지
    if "--no-start" not in sys.argv:
        if os.path.exists(MAIN_APP_PATH):
            print(" [실행] 신선 마스터 애플리케이션을 기동합니다...")
            try:
                subprocess.Popen([sys.executable.replace("python.exe", "pythonw.exe"), MAIN_APP_PATH],
                                 creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            except Exception as e_run:
                print(f" [오류] 마스터 실행 실패: {e_run}")
        else:
            print(" [오류] 실행할 마스터 파일(shinseon_master_app.pyw)이 존재하지 않습니다.")

if __name__ == "__main__":
    main()
