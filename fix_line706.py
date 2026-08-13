with open('core_logic.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'start_cooldown_countdown_timer' in l:
        lines[i] = '    async def start_cooldown_countdown_timer(self, duration_sec, reason_label="쿨타임"):\n'

with open('core_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Line 706 fixed successfully")
