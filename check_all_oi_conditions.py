import os, glob

def check_all_oi_conditions():
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                        lines = fp.readlines()
                        for idx, l in enumerate(lines):
                            if "oi_delta" in l and "> 0" in l and "target_oi" in l:
                                print(f"{path} [L{idx+1}]: {l.strip()}")
                except Exception:
                    pass

check_all_oi_conditions()