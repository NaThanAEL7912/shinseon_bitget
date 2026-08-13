import re

with open('shinseon_client_stripped.pyw', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Remove ccxt, aiohttp imports
code = re.sub(r'import ccxt.*?\n', '', code)
code = re.sub(r'import aiohttp.*?\n', '', code)

# 2. Add CSV button logic
csv_btn_code = '''
        # CSV 다운로드 버튼 추가
        self.btn_csv_download = QPushButton("📥 CSV 데이터 다운로드", right_widget)
        self.btn_csv_download.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DEBA9D, stop:1 #C5A07A);
                color: #0F0E0E;
                font-weight: bold;
                font-size: 12px;
                padding: 11px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #DEBA9D);
            }
        """)
        self.btn_csv_download.clicked.connect(self.request_csv_download)
        right_layout.addWidget(self.btn_csv_download)
'''

code = code.replace('right_layout.addStretch()', csv_btn_code + '\n        right_layout.addStretch()')

# 3. Add Websocket Client logic and CSV handler
ws_logic = '''
    def request_csv_download(self):
        if hasattr(self, 'ws') and self.ws:
            import json
            asyncio.create_task(self.ws.send(json.dumps({'type': 'csv_request'})))
            self.add_log("[CSV] 서버에 데이터 다운로드를 요청했습니다.")

    async def connect_websocket(self):
        url = 'ws://13.192.187.244:8765'
        while True:
            try:
                self.add_log(f"[Websocket] 일본 AWS 릴레이 서버 연결 시도: {url}")
                async with websockets.connect(url) as ws:
                    self.ws = ws
                    self.add_log("[Websocket] 서버 연결 성공!")
                    import json
                    await self.ws.send(json.dumps({'type': 'auth', 'secret': 'SECRET_TOKEN_HERE'}))
                    
                    async for message in ws:
                        data = json.loads(message)
                        if data.get('type') == 'update':
                            if 'price' in data:
                                self.current_price = float(data['price'])
                                self.lbl_price.setText(f"BTC/USDT 실시간 가격: {self.current_price:,.1f} USDT")
                            if 'log' in data:
                                self.add_log(data['log'])
                            if 'liq' in data:
                                self.bar_liq.setValue(int(data['liq']))
                                self.bar_liq.setFormat(f"1분 누적 청산: ${int(data['liq']):,} / $2.0M")
                        elif data.get('type') == 'csv_data':
                            csv_content = data.get('content')
                            with open('downloaded_data.csv', 'w', encoding='utf-8') as f:
                                f.write(csv_content)
                            self.add_log("[CSV] 데이터 다운로드 완료 및 저장 성공!")
            except Exception as e:
                self.add_log(f"[Websocket] 연결 오류: {e}. 3초 후 재시도...")
                await asyncio.sleep(3)
'''
code = code.replace('def add_log(self, text):', ws_logic + '\n    def add_log(self, text):')

# 4. Change config load
code = code.replace('.env', 'client_config.json')

# 5. Fix initialization in __main__
main_block = '''
if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    class DummyBot:
        v35_engine = None
        
    dashboard = ShinseonDashboard(DummyBot())
    dashboard.show()
    
    asyncio.create_task(dashboard.connect_websocket())
    
    with loop:
        loop.run_forever()
'''
code = re.sub(r'if __name__ == "__main__":.*', main_block, code, flags=re.DOTALL)

# Write to the final target file
with open('shinseon_client.pyw', 'w', encoding='utf-8') as f:
    f.write(code)
