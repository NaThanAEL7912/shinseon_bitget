import re
import os

file_path = "C:/Working/AntiGravity/ShinSeon_Bitget/shinseon_master_app.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 2. Add ccxt.bitget object creation
bitget_init_code = """        self.cdp_lock = asyncio.Lock()  # CDP 연결 동시 충돌 방지 락
        
        # 비트겟 CCXT 초기화
        self.bitget_exchange = None
        if env_vars.get("BITGET_API_KEY"):
            import ccxt.async_support as ccxt
            self.bitget_exchange = ccxt.bitget({
                'apiKey': env_vars.get("BITGET_API_KEY"),
                'secret': env_vars.get("BITGET_SECRET_KEY"),
                'password': env_vars.get("BITGET_PASSPHRASE"),
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
"""
content = content.replace("        self.cdp_lock = asyncio.Lock()  # CDP 연결 동시 충돌 방지 락", bitget_init_code)

# 3. Clean up playwright imports and RPA leftovers
# Remove playwright imports
content = re.sub(r'^\s*from playwright\.async_api import async_playwright\s*\n', '', content, flags=re.MULTILINE)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
