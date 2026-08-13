import ast
import json
import os

target_file = r"C:\Working\AntiGravity\ShinSeon_Bitget\shinseon_server.py"

with open(target_file, "r", encoding="utf-8") as f:
    source = f.read()

# We need to construct the new file which only includes BotCore, ShinseonV35Engine, 
# CCXT imports, basic logging, and standard libs.
# Then add a websocket server.

server_code = """
import sys
import os
import asyncio
import random
import logging
import time
import re
import json
import socket
import urllib.request
from datetime import datetime
from collections import deque
import aiohttp
import ssl

import ccxt.async_support as ccxt
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ShinseonBot")

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_server_config():
    config_path = os.path.join(BASE_DIR, "server_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Config load error: {e}")
    return {}

env_vars = load_server_config()

# ---- BOT CORE AND ENGINE ----
"""

# Extract BotCore and ShinseonV35Engine using simple string search since ast unparsing drops comments
lines = source.split('\n')

in_botcore = False
in_engine = False
botcore_lines = []
engine_lines = []

for line in lines:
    if line.startswith("class BotCore:"):
        in_botcore = True
        botcore_lines.append(line)
        continue
    if line.startswith("class ShinseonV35Engine:"):
        in_botcore = False
        in_engine = True
        engine_lines.append(line)
        continue
    
    if line.startswith("class ShinseonConfigDialog"):
        in_engine = False
        continue
        
    if in_botcore:
        botcore_lines.append(line)
    elif in_engine:
        engine_lines.append(line)

# Let's fix up some UI callbacks in BotCore and engine
# We'll just define the class as is, but we'll override ui_cb and chart_callback when we instantiate it.

server_code += "\n".join(botcore_lines)
server_code += "\n"
server_code += "\n".join(engine_lines)

server_code += """
# ==============================================================================
# Websocket Server for Hybrid Streaming
# ==============================================================================

class WsServer:
    def __init__(self, bot_core):
        self.bot_core = bot_core
        self.clients = set()
        self.last_chart_time = 0

    async def register(self, websocket):
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)

    async def broadcast_event(self, event_type, data):
        # 0s delay for events
        if not self.clients:
            return
        msg = json.dumps({"type": event_type, "data": data})
        for client in self.clients:
            asyncio.create_task(client.send(msg))
            
    async def broadcast_throttled(self, event_type, data):
        # 0.5s throttling
        now = time.time()
        if now - self.last_chart_time < 0.5:
            return
        self.last_chart_time = now
        if not self.clients:
            return
        msg = json.dumps({"type": event_type, "data": data})
        for client in self.clients:
            asyncio.create_task(client.send(msg))

ws_server = None

def ui_callback(current_price, log_type, msg, **kwargs):
    if ws_server:
        data = {"price": current_price, "log_type": log_type, "msg": msg}
        data.update(kwargs)
        # Event type message
        asyncio.create_task(ws_server.broadcast_event("ui_update", data))
    logger.info(f"[UI] {msg}")

def chart_callback(candles):
    if ws_server:
        asyncio.create_task(ws_server.broadcast_throttled("chart_update", candles))

async def main():
    global ws_server
    core = BotCore()
    ws_server = WsServer(core)
    
    # Websocket server setup
    async with websockets.serve(ws_server.register, "0.0.0.0", 8765):
        logger.info("Websocket server running on port 8765")
        await core.run_engine(ui_callback, chart_callback)

if __name__ == "__main__":
    asyncio.run(main())
"""

with open(target_file, "w", encoding="utf-8") as f:
    f.write(server_code)

print("Refactoring completed successfully.")
