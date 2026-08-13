import asyncio
import websockets
import json
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test_ws():
    uri = "ws://13.192.187.244:8765"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected! Listening for messages...")
            count = 0
            while count < 3:
                response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(response)
                msg_type = data.get('type')
                payload = data.get('data', {})
                print(f"\n[{time.strftime('%H:%M:%S')}] Received Type: {msg_type}")
                if msg_type == "ui_update":
                    print(f"  current_session: {payload.get('current_session')}")
                    print(f"  target_liq: {payload.get('target_liq')}")
                    print(f"  target_oi: {payload.get('target_oi')}")
                    print(f"  liq_10s: {payload.get('liq_10s')}")
                    count += 1
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_ws())
