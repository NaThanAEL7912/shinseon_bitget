import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://13.192.187.244:8765"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected! Sending CMD_SYNC_POSITION...")
            await ws.send(json.dumps({"cmd": "CMD_SYNC_POSITION"}))
            print("Sent! Waiting for response...")
            while True:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print("Received:", response)
                data = json.loads(response)
                if data.get('type') == 'EVT_SYNC_BALANCE':
                    print("SUCCESS! Received sync balance event.")
                    break
    except Exception as e:
        print("Error:", e)

asyncio.run(test_ws())
