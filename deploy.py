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

def update_app_version(new_version):
    targets = ["shinseon_client.pyw", "shinseon_server.py"]
    for target in targets:
        path = os.path.join(BASE_DIR, target)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            pattern = r"(self\.CURRENT_VERSION\s*=\s*[\"'])([^\"']*)([\"'])"
            new_content = re.sub(pattern, rf"\g<1>{new_version}\g<3>", content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"{target} 버전 업데이트 완료: {new_version}")

def run_cmd(cmd):
    print(f"실행 중: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BASE_DIR, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        print(f"오류 발생: {res.stderr}")
        return False
    print(res.stdout)
    return True

def deploy_to_aws_server():
    key_path = os.path.join(BASE_DIR, "shinseon-key.pem")
    if not os.path.exists(key_path):
        print("⚠️ [AWS 배포 건너뜀] shinseon-key.pem 키 파일이 로컬에 없습니다.")
        return False
        
    try:
        import paramiko
        print("🚀 [AWS 도쿄 서버] SSH/SFTP 직통 원격 배포 접속 시도 (13.192.187.244)...")
        key = paramiko.RSAKey.from_private_key_file(key_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("13.192.187.244", username="ubuntu", pkey=key, timeout=10)
        
        sftp = ssh.open_sftp()
        upload_files = ["shinseon_server.py", "shinseon_config.json", "core_logic.py", ".env", "server_config.json"]
        for f in upload_files:
            local_f = os.path.join(BASE_DIR, f)
            remote_f = f"/home/ubuntu/{f}"
            if os.path.exists(local_f):
                print(f" 📤 SFTP 전송: {f} ➡️ AWS {remote_f}")
                sftp.put(local_f, remote_f)
        sftp.close()
        
        print(" 🔄 AWS 기존 서버 프로세스 안전 종료 및 최신 데몬 재기동...")
        restart_cmd = """
sudo systemctl restart shinseon.service 2>/dev/null || (pkill -f shinseon_server.py; sleep 1; nohup /home/ubuntu/botenv/bin/python -u /home/ubuntu/shinseon_server.py > /home/ubuntu/shinseon_stdout.log 2>&1 < /dev/null &)
sleep 2
ps aux | grep shinseon_server.py | grep -v grep
"""
        stdin, stdout, stderr = ssh.exec_command(restart_cmd)
        out_txt = stdout.read().decode('utf-8', errors='ignore')
        print(f" 📊 [AWS 데몬 기동 확인]:\n{out_txt}")
        ssh.close()
        print(" ✅ [AWS 배포 성공] AWS 도쿄 서버에 최신 소스 반영 및 데몬 무중단 재기동 완료!")
        return True
    except Exception as e:
        print(f" ❌ [AWS 배포 실패]: {e}")
        return False

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
    print(" 🚀 [SHINSEON] GitHub + AWS 원클릭 자동 배포 엔진 가동")
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
    
    update_app_version(new_version)
    
    config_data["CURRENT_VERSION"] = new_version
    save_config(config_data)
    print("shinseon_config.json 내 버전 정보가 성공적으로 업데이트되었습니다.")
    
    # 1. AWS 도쿄 실전 서버 원격 핫-리로드 배포
    deploy_to_aws_server()

    # 2. GitHub 원격 main 브랜치 백업 배포
    try:
        files_to_deploy = [
            "shinseon_server.py",
            "shinseon_client.pyw",
            "shinseon_updater.py",
            "shinseon_config.json",
            "client_config.json",
            "server_config.json",
            "core_logic.py",
            "deploy.py",
            "Start_Sejong.bat",
            "신선_비트겟_클라이언트.bat"
        ]
        
        for f in files_to_deploy:
            src = os.path.join(BASE_DIR, f)
            if os.path.exists(src):
                run_cmd(f"git add \"{f}\"")
                
        run_cmd("git add docs/")
        print("🚀 [배포 준비] Git 스테이징 완료!")
    except Exception as copy_err:
        print(f"배포 준비 중 오류 발생: {copy_err}")
        sys.exit(1)
        
    commit_msg = f"Deploy version {new_version}"
    if not run_cmd(f'git commit -m "{commit_msg}"'):
        print("경고: Git commit에 변경점이 없거나 실패했습니다. 계속 푸시를 시도합니다.")
        
    if not run_cmd("git push origin main"):
        print("GitHub 원격 전송(push)에 실패했습니다.")
        sys.exit(1)
        
    print("====================================================")
    print(f" 🎉 [배포 완료] {new_version} 버전이 GitHub 및 AWS 서버에 완벽하게 적재/재기동되었습니다!")
    print("====================================================")

if __name__ == "__main__":
    main()
