import os

files_to_patch = [
    "core_logic.py",
    "shinseon_server.py",
    "SHINSEON_BlueDragon/core_logic.py",
    "SHINSEON_BlueDragon/shinseon_server.py"
]

patterns = [
    ("if rolling_1m_liq_usd >= target_liq and oi_delta_1m >= target_oi and oi_delta_1m > 0:", "if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:"),
    ("if rolling_1m_liq_usd >= target_liq and oi_delta_1m > 0 and oi_delta_1m >= target_oi:", "if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:"),
    ("if (rolling_1m_liq_usd >= target_liq) and (oi_delta_1m > 0 and oi_delta_1m >= target_oi):", "if (rolling_1m_liq_usd >= target_liq) and (abs(oi_delta_1m) >= target_oi):"),
]

for f in files_to_patch:
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as fp:
            code = fp.read()
        
        modified = False
        for p, r in patterns:
            if p in code:
                code = code.replace(p, r)
                modified = True
                print(f"[PATCHED] {f} -> {p[:30]}...")
                
        if modified:
            with open(f, "w", encoding="utf-8") as fp:
                fp.write(code)
            print(f"[SAVED] {f}")
        else:
            print(f"[ALREADY_CLEAN / NO_MATCH] {f}")