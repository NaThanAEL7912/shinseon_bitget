import os

def update_server_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    target = "if (rolling_1m_liq_usd >= target_liq) and (oi_delta_1m > 0 and oi_delta_1m >= target_oi):"
    replacement = "if (rolling_1m_liq_usd >= target_liq) and (abs(oi_delta_1m) >= target_oi):"
    
    if target in code:
        code = code.replace(target, replacement)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"Updated successfully: {filepath}")
    else:
        print(f"Target pattern not found in: {filepath}")

update_server_file("shinseon_server.py")
update_server_file("SHINSEON_BlueDragon/shinseon_server.py")