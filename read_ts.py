with open(r"C:\Users\ClawNaEL\.gemini\antigravity\brain\ee372d50-927a-4c14-aa25-d1f50464ecf7\.system_generated\steps\16835\content.md", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'id=["'']place-trailing-stop-order["'']', text)
if m:
    print(text[m.start():m.start()+3000])