import sys
import re

file_path = r'C:\Working\AntiGravity\ShinSeon_Bitget\shinseon_master_app.pyw'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# find the do_position_sync function
match = re.search(r'    async def do_position_sync\(self\):.*?        finally:\n            self\.btn_position_sync\.setEnabled\(True\)\n            self\.btn_position_sync\.setText\("🔄 포지션 동기화"\)\n', content, re.DOTALL)
if match:
    new_code = '''    async def do_position_sync(self):
        try:
            if not getattr(self.bot_core, 'bitget_exchange', None):
                self.add_log("❌ [동기화 실패] CCXT Bitget 거래소 객체가 존재하지 않습니다.")
                return

            positions = await self.bot_core.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])
            
            active_pos = None
            for pos in positions:
                contracts = float(pos.get('contracts', 0.0))
                if contracts > 0:
                    direction = "LONG" if pos.get('side', '').lower() == 'long' else "SHORT"
                    entry_price = float(pos.get('entryPrice', 0.0))
                    vol = int(round(contracts * 1000))
                    pos_id = pos.get('id', '')
                    active_pos = {
                        "direction": direction,
                        "entryPrice": entry_price,
                        "positionIds": [pos_id] if pos_id else [],
                        "volume": vol
                    }
                    break
                    
            if active_pos:
                direction = active_pos["direction"]
                entry_price = active_pos["entryPrice"]
                pos_ids = active_pos.get("positionIds", [])
                
                if self.bot_core.v35_engine:
                    if not self.bot_core.v35_engine.is_position_active or self.bot_core.v35_engine.entry_direction != direction:
                        self.bot_core.v35_engine.peak_pnl_pct = 0.0
                    self.bot_core.v35_engine.is_position_active = True
                    self.bot_core.v35_engine.entry_direction = direction
                    self.bot_core.v35_engine.entry_price = entry_price
                    # [3차 방어선] pos_ids가 빈 목록이더라도 기존 엔진이 확보한 active_position_ids가 있으면 유지
                    if pos_ids:
                        self.bot_core.v35_engine.active_position_ids = pos_ids
                    elif not self.bot_core.v35_engine.active_position_ids:
                        self.bot_core.v35_engine.active_position_ids = []
                    self.bot_core.v35_engine.position_volume = active_pos.get("volume", 1)
                    
                    # [신설]: 동기화 성공 시 자고 있던 가드레일 루프 즉시 자동 기상!
                    if not getattr(self.bot_core.v35_engine, "is_guardrail_running", False):
                        import asyncio
                        asyncio.create_task(self.bot_core.v35_engine.manage_v35_exit_guardrail(direction))
                        self.add_log(f"⚡ [가드레일 자동 기상] 동기화 성공! 자고 있던 출구 감시 루프가 즉시 기상하여 실시간 감시를 개시합니다. (방향: {direction})")
                    
                self.lbl_guardrail.setText(f"진입/청산 상태:\\n[{direction} 진입 완료] 단가: {entry_price:,.0f}")
                self.add_log(f"✔ [동기화 완료] 열린 포지션 감지: {direction} @ {entry_price:,.1f} USD (ID 목록: {pos_ids})")
            else:
                if self.bot_core.v35_engine:
                    self.bot_core.v35_engine.is_position_active = False
                    self.bot_core.v35_engine.entry_price = 0.0
                    self.bot_core.v35_engine.position_volume = 0
                    self.bot_core.v35_engine.entry_direction = ""
                    self.bot_core.v35_engine.is_half_exited = False
                    self.bot_core.v35_engine.has_pyramided = False
                    self.bot_core.v35_engine.has_second_entry = False
                    self.bot_core.v35_engine.has_third_entry = False
                    self.bot_core.v35_engine.has_smart_guarded = False
                    self.bot_core.v35_engine.exit_in_progress = False
                self.lbl_guardrail.setText("진입/청산 상태:\\n[100% 현금 대기 중]")
                self.add_log("✔ [동기화 완료] 열려있는 포지션이 없습니다. (100% 현금)")
            
            self.add_log("🌓 [수동 리로드] BITGET 포지션 상태를 강제로 재동기화 완료하였습니다.")
            
        except Exception as e:
            self.add_log(f"❌ [동기화 실패] 포지션 스캔 중 오류 발생: {e}")
        finally:
            self.btn_position_sync.setEnabled(True)
            self.btn_position_sync.setText("🔄 포지션 동기화")
'''
    content = content[:match.start()] + new_code + content[match.end():]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Successfully patched do_position_sync')
else:
    print('Could not find the target block!')
