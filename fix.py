import re

with open('c:/Working/SHINSEON/shinseon_master_app.pyw', 'r', encoding='utf-8') as f:
    text = f.read()

def repl(m):
    indent = m.group(1)
    return m.group(0) + f'\n{indent}self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")\n{indent}self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0'

new_text = re.sub(r'(^[ \t]*)self\.last_exit_trigger_price\s*=\s*(current_bitget_price|binance_mid)', repl, text, flags=re.MULTILINE)

with open('c:/Working/SHINSEON/shinseon_master_app.pyw', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Done!')
