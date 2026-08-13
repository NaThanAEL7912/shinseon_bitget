import os

print("====================================================")
print("🔍 2026-08-11 03:36:54 KST 오늘 로그 수색")
print("====================================================")

for root, dirs, files in os.walk('/home/ubuntu'):
    for file in files:
        if '2026-08-11' in file or 'today' in file or file.endswith('.log'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if '03:36' in content:
                    print(f"\nFOUND IN FILE: {path}")
                    lines = content.splitlines()
                    for idx, l in enumerate(lines):
                        if '03:36' in l or '03:35' in l or '03:37' in l or '03:39' in l:
                            print(f"  L{idx+1}: {l}")
            except Exception as e:
                pass
