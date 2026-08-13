with open('core_logic.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = 'rem_sec = 60.0 - elapsed_entry\n                        if getattr(self.bot, "dashboard", None):\n                            self.bot.dashboard.add_log(f"🛡️ [진입 60초 안전 락다운] 진입 직후 60초간 반대 청산 무조건 유예 중 (남은 시간: {rem_sec:.1f}초) ➡️ 휩소 청산 100% 차단")'
replacement = target + '\n                    return'

if target in content:
    content = content.replace(target, replacement)
    with open('core_logic.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Return statement added successfully to core_logic.py")
else:
    print("Target block not found, searching alternative...")
    # fallback line insertion
    lines = content.splitlines(True)
    for i, line in enumerate(lines):
        if '🛡️ [진입 60초 안전 락다운]' in line:
            lines.insert(i + 1, '                    return\n')
            break
    with open('core_logic.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Return inserted via line search")
