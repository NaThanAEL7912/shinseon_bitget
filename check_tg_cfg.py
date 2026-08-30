import json, os
cfg_path = '/home/ubuntu/server_config.json'
if os.path.exists(cfg_path):
    with open(cfg_path, 'r') as f:
        cfg = json.load(f)
        token = cfg.get('telegram_token') or cfg.get('TELEGRAM_BOT_TOKEN') or cfg.get('TELEGRAM_TOKEN') or ''
        chat_id = cfg.get('telegram_chat_id') or cfg.get('TELEGRAM_CHAT_ID') or ''
        print(f"TELEGRAM_CONFIGURED: Token_len={len(token)}, ChatId={chat_id}")
else:
    print("NO_SERVER_CONFIG")