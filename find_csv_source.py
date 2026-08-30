import os, glob

for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py') or f.endswith('.csv') or f.endswith('.log'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    if 'STOPPED' in content or 'NONE' in content and '1500000' in content:
                        print(f"MATCH: {path}")
            except Exception:
                pass