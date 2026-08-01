import re
file_path = "C:/Working/AntiGravity/ShinSeon_Bitget/shinseon_master_app.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

def replace_func_body(text, func_name):
    pattern = r'(async def ' + func_name + r'\(self.*?\):)(.*?)(?=\n    (?:async )?def |\Z)'
    def repl(m):
        return m.group(1) + '\n        pass\n'
    return re.sub(pattern, repl, text, flags=re.DOTALL)

content = replace_func_body(content, 'run_token_sniffer')
content = replace_func_body(content, 'restart_chrome_debug_port')
content = replace_func_body(content, 'trigger_bitget_rpa_test')
content = replace_func_body(content, 'execute_bitget_emergency_master_internal')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
