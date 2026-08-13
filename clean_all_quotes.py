import re

with open('core_logic.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Check string literal balance
    # Count double quotes outside comments
    code_part = line.split('#')[0]
    dq_count = code_part.count('"')
    if dq_count % 2 != 0:
        # replace unclosed quotes or invalid characters
        line = re.sub(r'"[^"\n]*$', '"안전 모드")', line)
    new_lines.append(line)

with open('core_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Quotes cleaned")
