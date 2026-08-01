import os
import sys
import json
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "shinseon_config.json")

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
    except Exception as e:
        print(f"설정 파일 저장 실패: {e}")

def increment_version(version_str):
    cleaned = version_str.strip().upper()
    prefix = "B"
    if cleaned.startswith("V") or cleaned.startswith("B"):
        prefix = cleaned[0]
        cleaned = cleaned[1:]
    else:
        prefix = "B"
    parts = cleaned.split(".")
    try:
        if parts:
            parts[-1] = str(int(parts[-1]) + 1)
            return prefix + ".".join(parts)
    except ValueError:
        pass
    return version_str + "_new"

def update_master_app_version(new_version):
    main_app_path = os.path.join(BASE_DIR, "shinseon_master_app.pyw")
    if os.path.exists(main_app_path):
        try:
            with open(main_app_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            pattern = r"(self\.CURRENT_VERSION\s*=\s*[\"'])([^\"']*)([\"'])"
            new_content = re.sub(pattern, rf"\g<1>{new_version}\g<3>", content)
            with open(main_app_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"shinseon_master_app.pyw 내 self.CURRENT_VERSION을 {new_version}으로 자동 업데이트했습니다.")
            return True
        except Exception as e:
            print(f"shinseon_master_app.pyw 버전 치환 실패: {e}")
    else:
        print("shinseon_master_app.pyw 파일을 찾을 수 없습니다.")
    return False

def run_cmd(cmd):
    print(f"실행 중: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BASE_DIR, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        print(f"오류 발생: {res.stderr}")
        return False
    print(res.stdout)
    return True

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
    print(" 🚀 [SHINSEON] GitHub 원클릭 자동 배포 엔진 가동")
    print("====================================================")
    
    config_data = load_config()
    current_version = config_data.get("CURRENT_VERSION", "v1.4")
    print(f"현재 로컬 버전: {current_version}")
    
    new_version = None
    if len(sys.argv) > 1:
        arg_ver = sys.argv[1].strip()
        upper_arg = arg_ver.upper()
        if upper_arg.startswith("V") or upper_arg.startswith("B"):
            new_version = upper_arg
        else:
            new_version = "B" + arg_ver
            
    if not new_version:
        new_version = increment_version(current_version)
        
    print(f"배포 예정 신규 버전: {new_version}")
    
    update_master_app_version(new_version)
    
    config_data["CURRENT_VERSION"] = new_version
    save_config(config_data)
    print("shinseon_config.json 내 버전 정보가 성공적으로 업데이트되었습니다.")
    
    # [SHINSEON_BlueDragon] 배포용 폴더 구조 생성 및 파일 복사
    target_deploy_dir = os.path.join(BASE_DIR, "SHINSEON_BlueDragon")
    os.makedirs(target_deploy_dir, exist_ok=True)
    os.makedirs(os.path.join(target_deploy_dir, "docs"), exist_ok=True)
    
    import shutil
    try:
        shutil.copy2(os.path.join(BASE_DIR, "shinseon_master_app.pyw"), os.path.join(target_deploy_dir, "shinseon_master_app.pyw"))
        shutil.copy2(os.path.join(BASE_DIR, "shinseon_config.json"), os.path.join(target_deploy_dir, "shinseon_config.json"))
        
        license_src = os.path.join(BASE_DIR, "docs", "license.json")
        if os.path.exists(license_src):
            shutil.copy2(license_src, os.path.join(target_deploy_dir, "docs", "license.json"))
        print("🚀 [배포 준비] SHINSEON_BlueDragon 하위 폴더로 복사 완료!")
    except Exception as copy_err:
        print(f"배포 폴더 복사 중 오류 발생: {copy_err}")
        sys.exit(1)
        
    if not run_cmd("git add SHINSEON_BlueDragon/"):
        print("Git add 실패로 배포를 중단합니다.")
        sys.exit(1)
        
    commit_msg = f"Deploy version {new_version}"
    if not run_cmd(f'git commit -m "{commit_msg}"'):
        print("경고: Git commit에 변경점이 없거나 실패했습니다. 계속 푸시를 시도합니다.")
        
    if not run_cmd("git push origin master"):
        print("GitHub 원격 전송(push)에 실패했습니다.")
        sys.exit(1)
        
    print("====================================================")
    print(f" 🎉 [배포 완료] {new_version} 버전이 GitHub 배포 서버에 완벽하게 적재되었습니다!")
    print("====================================================")

if __name__ == "__main__":
    main()
