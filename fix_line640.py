with open('core_logic.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

new_lines = [l for i, l in enumerate(lines) if not (i+1 == 640 and 'ui_callback' in l)]

with open('core_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Line 640 removed successfully")
