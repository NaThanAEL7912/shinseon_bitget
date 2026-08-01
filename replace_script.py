import sys
import traceback

file_path = r'C:\Working\AntiGravity\ShinSeon_Bitget\shinseon_master_app.pyw'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if 'async with self.bot.cdp_lock:' in line and 'pw = await async_playwright().start()' in lines[i+2]:
        start_idx = i
        break

if start_idx != -1:
    for i in range(start_idx, len(lines)):
        if 'async def check_radar_signal_dynamic(' in lines[i]:
            end_idx = i
            break

if start_idx != -1 and end_idx != -1:
    print(f'Found from {start_idx} to {end_idx}')
    
    new_code = """        async with self.bot.cdp_lock:
            # --- [Phase 2] 신선 비트겟 API CCXT 연동 이식 (Playwright 제거) ---
            async def _do_ccxt_order():
                try:
                    exchange = self.bot.bitget_exchange
                    if not exchange:
                        self.bot.ui_cb(0.0, 0, "❌ [비트겟 API 에러] CCXT 객체가 초기화되지 않았습니다.")
                        return False

                    symbol = 'BTC/USDT:USDT'
                    current_price = getattr(self.bot, "current_price", 60000.0)
                    bitget_bal = getattr(self.bot, "bitget_balance", 0.0)
                    if bitget_bal <= 0.0:
                        bitget_bal = self.bot.c_total

                    dashboard = getattr(self.bot, "dashboard", None)
                    if not dashboard:
                        return False
                        
                    if side == "CLEAR":
                        if order_type == "CANCEL_ALL":
                            open_orders = await exchange.fetch_open_orders(symbol)
                            for o in open_orders:
                                await exchange.cancel_order(o['id'], symbol)
                            self.bot.ui_cb(0.0, 0, "🎯 [스탑로스 취소 완료] 미체결 스탑 주문 취소 완료")
                            return True

                        positions = await exchange.fetch_positions([symbol])
                        active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0), None)
                        if not active_pos:
                            self.bot.ui_cb(0.0, 0, "⚠️ [청산 스킵] 현재 활성화된 포지션이 없습니다.")
                            self.is_position_active = False
                            self.position_volume = 0
                            self.exit_in_progress = False
                            return True
                        
                        pos_side = active_pos['side']
                        close_side = 'sell' if pos_side == 'long' else 'buy'
                        
                        ratio_factor = custom_ratio if custom_ratio > 0.0 else 0.5
                        if order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE":
                            amount = float(active_pos['contracts']) * ratio_factor
                            pct_lbl = int(round(ratio_factor * 100))
                            self.bot.ui_cb(0.0, 0, f"🎯 [{pct_lbl}% 청산] API 발주 시작...")
                        else:
                            amount = float(active_pos['contracts'])
                            self.bot.ui_cb(0.0, 0, "🎯 [전량 청산] API 발주 시작...")
                            
                        amount = max(0.001, round(amount, 3))
                        
                        try:
                            order = await exchange.create_order(symbol, 'market', close_side, amount, params={'reduceOnly': True})
                            self.bot.ui_cb(0.0, 0, f"✅ [청산 성공] 주문 완료: {amount} BTC")
                        except Exception as e:
                            self.bot.ui_cb(0.0, 0, f"❌ [청산 에러] 비트겟 API 예외 발생: {e}")
                            return False
                        
                        if order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE":
                            self.position_volume = max(0, self.position_volume - int(round(amount * 1000)))
                            self.is_half_exited = True
                        else:
                            self.is_position_active = False
                            self.position_volume = 0
                            self.entry_price = 0.0
                            self.entry_direction = ""
                            self.has_second_entry = False
                            self.has_third_entry = False
                            self.exit_in_progress = False
                            
                            profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0))
                            loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0))
                            exit_reason_text = getattr(self, "exit_reason", "")
                            is_loss = ("손절" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("스탑" in exit_reason_text and "익절" not in exit_reason_text)
                            target_cooldown = loss_cd_sec if is_loss else profit_cd_sec
                            label = "손절 쿨타임" if is_loss else "익절/스위칭 쿨타임"
                            
                            self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                            if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                                self.cooldown_timer_task.cancel()
                            self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
                            
                    elif side == "STOP_LOSS":
                        self.bot.ui_cb(0.0, 0, "🎯 [스탑 완료] 스탑로스 API 발주 (현재 모니터링 감지로 대체됨)")
                        
                    else:
                        ccxt_side = 'buy' if side == 'LONG' else 'sell'
                        
                        if order_type == "ADD_PYRAMIDING":
                            p_vol = getattr(self, "position_volume", 0) / 1000.0
                            pyra_ratio = getattr(dashboard, "pyramiding_ratio", 30.0) / 100.0
                            original_vol = p_vol * 2 if self.is_half_exited else p_vol
                            amount = original_vol * pyra_ratio
                        else:
                            if order_type == "ADD_THIRD_ENTRY":
                                ratio = dashboard.split_entry_3_ratio
                            elif order_type == "ADD_100_PERCENT":
                                ratio = dashboard.split_entry_2_ratio
                            else:
                                ratio = dashboard.split_entry_1_ratio
                                
                            if ratio <= 0.0:
                                return False
                            p_target = max(1000.0, bitget_bal * (ratio / 100.0))
                            amount = p_target / current_price
                            
                        amount = max(0.001, round(amount, 3))
                        
                        self.bot.ui_cb(0.0, 0, f"🎯 [진입 발주] {side} {amount} BTC 시장가 주문 시작...")
                        try:
                            order = await exchange.create_order(symbol, 'market', ccxt_side, amount)
                            self.bot.ui_cb(0.0, 0, f"✅ [진입 성공] {side} {amount} BTC 체결 완료")
                        except Exception as e:
                            self.bot.ui_cb(0.0, 0, f"❌ [진입 에러] 비트겟 API 예외 발생: {e}")
                            return False
                        
                        vol_int = int(round(amount * 1000))
                        if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
                            old_vol = getattr(self, "position_volume", 0)
                            new_vol = old_vol + vol_int
                            if new_vol > 0:
                                self.entry_price = (self.entry_price * old_vol + current_price * vol_int) / new_vol
                            self.position_volume = new_vol
                        else:
                            self.entry_price = current_price
                            self.entry_price_1 = current_price
                            self.position_volume = vol_int
                            self.is_position_active = True
                            self.entry_direction = side
                            self.last_entry_time = time.time()
                    return True
                except Exception as e:
                    traceback.print_exc()
                    self.bot.ui_cb(0.0, 0, f"❌ [주문 에러] 비트겟 API 예외 처리 중 오류: {e}")
                    if side == "CLEAR":
                        self.exit_in_progress = False
                    return False

            # 비동기(Non-blocking) 백그라운드 태스크로 주문 던지기
            asyncio.create_task(_do_ccxt_order())
            return True

"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        for i in range(start_idx):
            f.write(lines[i])
        f.write(new_code)
        for i in range(end_idx - 1, len(lines)): # keep the empty line before check_radar_signal_dynamic
            f.write(lines[i])
            
    print('Replacement complete.')
else:
    print('Failed to find start or end index.')
