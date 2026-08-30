with open("shinseon_server.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "telegram" in l.lower() or "send_tg" in l.lower() or "send_telegram" in l.lower() or "process_1m_data" in l.lower() or "signal" in l.lower():
        if any(k in l.lower() for k in ["def ", "send", "msg", "bot_token", "chat_id"]):
            print(f"L{i+1}: {l.strip()[:100]}")