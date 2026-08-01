import os
import re

directory = r"c:\Working\AntiGravity\ShinSeon_Bitget"
extensions = ('.py', '.pyw', '.json')

replacements = [
    (r'\bbitget\b', 'bitget'),
    (r'\bbitget\b', 'bitget'),
    (r'\bBITGET\b', 'BITGET'),
    (r'\bBITGET\b', 'BITGET'),
    (r'\bBitget\b', 'Bitget'),
    (r'\bBitget\b', 'Bitget'),
    (r'비트겟', '비트겟')
]

# We need to compile the regexes
compiled_replacements = [(re.compile(pattern), repl) for pattern, repl in replacements]

# also handle cases where 'bitget' or 'bitget' are part of another word, like `m_bitget` -> `m_bitget`
# so I shouldn't use \b for all cases?
# Let's see: `execute_bitget_internal_packet` -> `execute_bitget_internal_packet`. `\b` works here because `_` is a word boundary.
# Wait, `\b` considers `_` as part of the word (\w). So `m_bitget` and `\bbitget\b` will NOT match, because `_` is a word character.
# Ah! \w is [a-zA-Z0-9_]. So \b is the boundary between \w and \W.
# Therefore, `\bbitget\b` will not match `m_bitget` or `execute_bitget`.
# Let's use `(?i)bitget` but then we lose exact case matching.
# Better to write a custom replacement function.

def replace_cases(match):
    word = match.group(0)
    if word == 'bitget': return 'bitget'
    if word == 'bitget': return 'bitget'
    if word == 'BITGET': return 'BITGET'
    if word == 'BITGET': return 'BITGET'
    if word == 'Bitget': return 'Bitget'
    if word == 'Bitget': return 'Bitget'
    # For mixed cases like Bitget, just return as is, or lowercase
    if word.lower() == 'bitget':
        if word.isupper(): return 'BITGET'
        if word[0].isupper(): return 'Bitget'
        return 'bitget'
    if word.lower() == 'bitget':
        if word.isupper(): return 'BITGET'
        if word[0].isupper(): return 'Bitget'
        return 'bitget'
    return word

pattern = re.compile(r'bitget|bitget', re.IGNORECASE)

modified_files = []

for root, dirs, files in os.walk(directory):
    if '.git' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith(extensions):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"Failed to read {filepath}: {e}")
                continue
                
            new_content = pattern.sub(replace_cases, content)
            new_content = new_content.replace('비트겟', '비트겟')
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                modified_files.append(filepath)
                print(f"Modified: {filepath}")

print(f"Total modified files: {len(modified_files)}")
