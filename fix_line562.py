with open('core_logic.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'async with websocket_conn as websocket:' in l:
        lines[i] = '                websocket_conn = await asyncio.wait_for(websockets.connect(uri), timeout=2.0)\n                async with websocket_conn as websocket:\n'

with open('core_logic.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Line 562 fixed successfully")
