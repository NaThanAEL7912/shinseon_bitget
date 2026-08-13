import re

with open('shinseon_client.pyw', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace do_sync_balances completely
code = re.sub(r'async def do_sync_balances\(self\):.*?(?=\n    def )', r'async def do_sync_balances(self):\n        self.add_log("[뷰어 모드] 잔고 동기화는 서버에서 처리됩니다.")\n        self.btn_sync_balance.setEnabled(True)\n        self.btn_sync_balance.setText("🔄 실전 계좌 잔고 동기화")', code, flags=re.DOTALL)

# Replace do_latency_test completely
code = re.sub(r'async def do_latency_test\(self\):.*?(?=\n    def )', r'async def do_latency_test(self):\n        self.add_log("[뷰어 모드] 레이턴시 실측은 지원하지 않습니다.")', code, flags=re.DOTALL)

# Remove env loading
code = re.sub(r'def load_env_file\(\):.*?(?=\n# 로깅 설정)', r'def load_env_file():\n    return {"SECRET_TOKEN": "YOUR_SECRET_TOKEN"}\n\nenv_vars = load_env_file()\n', code, flags=re.DOTALL)

with open('shinseon_client.pyw', 'w', encoding='utf-8') as f:
    f.write(code)
