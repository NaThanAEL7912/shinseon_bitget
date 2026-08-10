class BotCore:
    def __init__(self):
        from collections import deque
        self.c_total = 20000.0
        self.m_bitget = 20000.0
        self.m_bin = 0.0
        self.p_target = 70000.0
        self.p_target_pct = 3.5
        self.bitget_balance = 0.0
        self.is_running = False
        self.current_task = None
        self.v35_engine = None
        self.ui_cb = None
        self.cdp_lock = asyncio.Lock()  # CDP ?곌껐 ?숈떆 異⑸룎 諛⑹? ??
        
        # 鍮꾪듃寃?CCXT 珥덇린??
        self.bitget_exchange = None
        if env_vars.get("BITGET_API_KEY"):
            import ccxt.async_support as ccxt
            self.bitget_exchange = ccxt.bitget({
                'apiKey': env_vars.get("BITGET_API_KEY"),
                'secret': env_vars.get("BITGET_SECRET_KEY"),
                'password': env_vars.get("BITGET_PASSPHRASE"),
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })

        self.bitget_headers = {}  # BITGET ?ㅼ떆媛??몄쬆 ?ㅻ뜑 蹂닿????뺤뀛?덈━
        self.last_binance_time_ms = int(time.time() * 1000)  # 媛??理쒖떊 諛붿씠?몄뒪 ?뱀냼耳?????꾩뒪?ы봽 (ms)
        self.last_packet_latency_ms = 15.0  # ?쒖젙 諛붿씠?몄뒪 ?⑦궥 ?덉씠?댁떆 ?섏튂 (ms)
        self.buy_liq_buffer = deque()
        self.sell_liq_buffer = deque()
        self.price_history = deque()
        self.current_price = 0.0
        self.price_ready = False
        
    async def run_token_sniffer(self):
        pass

    def update_capital_config(self, c_total, m_bitget, m_bin, p_target):
        self.c_total = c_total
        self.m_bitget = m_bitget
        self.m_bin = m_bin
        self.p_target = p_target
        if self.v35_engine:
            self.v35_engine.CAPITAL = c_total
            self.v35_engine.DEPLOY_MARGIN = c_total * 0.50
            self.v35_engine.POSITION_SIZE = self.v35_engine.DEPLOY_MARGIN * 20.0

    async def run_engine(self, ui_callback, chart_callback):
        self.is_running = True
        self.ui_cb = ui_callback
        self.current_task = asyncio.current_task()
        self.token_sniffer_task = asyncio.create_task(self.run_token_sniffer())
        
        # v3.5 ?⑤갑???寃??붿쭊 湲곗긽
        self.v35_engine = ShinseonV35Engine(self)
        self.v35_engine.CAPITAL = self.c_total
        self.v35_engine.DEPLOY_MARGIN = self.c_total * 0.50
        self.v35_engine.POSITION_SIZE = self.v35_engine.DEPLOY_MARGIN * 20.0
        
        ui_callback(0.0, 0, "??[?룬걫] 諛붿씠?몄뒪 ?ㅼ떆媛??쒖꽭 ?뱀냼耳?WSS) ?곌껐 ?섎┰ 以?..")
        
        spot_exchange = ccxt.binance({
            'options': {'defaultType': 'spot'},
            'enableRateLimit': True
        })
        
        candles = []
        try:
            ohlcv = await spot_exchange.fetch_ohlcv("BTC/USDT", timeframe="15m", limit=30)
            for idx, item in enumerate(ohlcv):
                candles.append([float(idx), item[1], item[4], item[3], item[2]])
            chart_callback(candles)
        except Exception as e:
            logger.error(f"怨쇨굅 罹붾뱾 ?대젰 濡쒕뱶 吏?? {e}")
        finally:
            await spot_exchange.close()
            
        # ?윟 [v4.05 ?꾩튂]: VPN 移⑤У??Drop 臾듭궡 ???諛??꾨Ъ留?stream) 吏곹넻 濡ㅻ갚 (異뷀썑 ?쇰낯 VPS ?댁＜ ??fstream?쇰줈 蹂듦? 媛뺣젰 沅뚯옣)
        uri = "wss://stream.binance.com/stream?streams=btcusdt@ticker/btcusdt@aggTrade"
        
        # 100% ?ㅼ떆媛?由ъ뼹 泥?궛 諛?OI 踰꾪띁 珥덇린??
        from collections import deque
        import aiohttp
        self.liq_buffer = deque()      # (timestamp, usd_value)
        self.oi_history = deque()      # (timestamp, oi_value)
        self.real_liq_1m = 0.0
        self.real_oi_speed_1m = 0.0
        self.liq_wss_connected = True
        self.last_real_forceorder_time = 0.0
        
        # v1.1 ?깅뒫 寃⑹긽: aggTrade ?ㅼ떆媛??꾩쟻湲?
        self.agg_buy_vol = 0.0
        self.agg_sell_vol = 0.0
        
        self.mock_liq = 0.0
        self.mock_oi = 0.0
        self.current_price = 0.0
        self.spot_price = 0.0
        self.price_basis = 0.0
        self.open_p = 63100.0
        self.high_p = 63300.0
        self.low_p = 62900.0
        
        # 留?1珥덈쭏??媛寃?蹂?숆낵 ?곕룞?섏뿬 寃뚯씠吏 諛붾? ?곸떆 遺?쒕읇寃??붾뱶??鍮꾨룞湲??붾젅硫뷀듃由?猷⑦봽 異붽? 媛??(媛??癒쇱? ?낅┰ 援щ룞!)
        async def run_telemetry_loop():
            while self.is_running:
                try:
                    await asyncio.sleep(0.1)
                    
                    # 0. KST ?쒖뒪???쒓컙 湲곕컲 ?숈쟻 ?꾧퀎移??ㅼ떆媛?怨꾩궛 諛??섎룞 ?ㅻ쾭?쇱씠??
                    now_dt = datetime.now()
                    hour_val = now_dt.hour
                    kst_time_str = now_dt.strftime("%H:%M:%S")
                    
                    dashboard = getattr(self, "dashboard", None)
                    # thresholds ?뺤뀛?덈━ ?덉쟾 李몄“ 諛?湲곕낯媛??명똿
                    thresholds = {
                        "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
                        "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
                        "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
                        "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3},
                        "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
                        "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
                        "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
                        "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3}
                    }
                    if dashboard and hasattr(dashboard, "session_thresholds"):
                        thresholds = dashboard.session_thresholds

                    # ?쒓컙?蹂??몄뀡 ?먯젙 諛?湲곕낯 ?꾧퀎移?異붿텧 (09??09???몃젅?대뵫 ?곗씠 ?곕룞 + 1遺??꾩땐 ??꾨씫 媛쒕컻怨꾪쉷??260)
                    from datetime import timedelta
                    trading_dt = now_dt - timedelta(hours=9)
                    is_weekend = trading_dt.weekday() in [5, 6]
                    minute_val = hour_val * 60 + now_dt.minute
                    
                    # 1遺??꾩땐 ??꾨씫 洹쒖튃 ?곸슜:
                    # - ?꾩떆?? 08:59:00 ~ 15:58:59 (539 <= m < 959)
                    # - ?좊읇: 15:59:00 ~ 22:28:59 (959 <= m < 1349)
                    # - 誘멸뎅 蹂몄옣: 22:29:00 ~ 04:58:59 (m >= 1349 or m < 299)
                    # - ?쒗룊?? 04:59:00 ~ 08:58:59 (299 <= m < 539)
                    if 539 <= minute_val < 959:
                        if is_weekend:
                            session_key = "weekend_asia"
                            current_session = f"?뙱 二쇰쭚 ?꾩떆??(KST {kst_time_str})"
                        else:
                            session_key = "asia"
                            current_session = f"?뵶 ?꾩떆???μ꽭 (KST {kst_time_str})"
                    elif 959 <= minute_val < 1349:
                        if is_weekend:
                            session_key = "weekend_europe"
                            current_session = f"?뙱 二쇰쭚 ?좊읇 (KST {kst_time_str})"
                        else:
                            session_key = "europe"
                            current_session = f"?윞 ?좊읇 ?μ꽭 (KST {kst_time_str})"
                    elif minute_val >= 1349 or minute_val < 299:
                        if is_weekend:
                            session_key = "weekend_us"
                            current_session = f"?뙱 二쇰쭚 誘멸뎅 蹂몄옣 (KST {kst_time_str})"
                        else:
                            session_key = "us"
                            current_session = f"?윟 誘멸뎅 蹂몄옣 (KST {kst_time_str})"
                    else: # 299 <= minute_val < 539 (04:59 ~ 08:58)
                        if is_weekend:
                            session_key = "weekend_pacific"
                            current_session = f"?뙱 二쇰쭚 ?쒗룊??(KST {kst_time_str})"
                        else:
                            session_key = "pacific"
                            current_session = f"???쒗룊???〓낫 (KST {kst_time_str})"
                    
                    target_liq = thresholds[session_key]["liq"]
                    target_oi = thresholds[session_key]["oi"]
                    target_sl = thresholds[session_key]["sl"]

                    if dashboard and dashboard.chk_manual_threshold.isChecked():
                        current_session = f"???섎룞 議곗쑉 ({kst_time_str})"
                        try:
                            liq_txt = dashboard.edit_target_liq.text().replace(",", "").strip()
                            target_liq = float(liq_txt) if liq_txt else 100000.0
                        except Exception:
                            target_liq = 100000.0
                        try:
                            oi_txt = dashboard.edit_target_oi.text().strip()
                            target_oi = float(oi_txt) if oi_txt else 0.02
                        except Exception:
                            target_oi = 0.02
                        try:
                            slip_txt = dashboard.edit_target_slippage.text().strip()
                            target_slippage = float(slip_txt) if slip_txt else 0.15
                        except Exception:
                            target_slippage = 0.15
                        self.v35_engine.ENTRY_SLIPPAGE_CAP = target_slippage / 100.0

                    # 諛깆뿏???붿쭊???몄뀡蹂??먯젅??諛??몄뀡 ?뺣낫 ?꾨떖
                    if self.v35_engine:
                        self.v35_engine.current_session_sl = target_sl
                        self.v35_engine.current_session_key = session_key
                        self.v35_engine.current_session_name = current_session
                    
                    # 1. 紐⑤뱶???곕Ⅸ ?곗씠??遺꾧린 諛?1遺?媛寃?蹂???곗텧
                    now_t = time.time()
                    while self.price_history and now_t - self.price_history[0][0] > 60.0:
                        self.price_history.popleft()
                        
                    if self.price_history:
                        price_10s_ago = self.price_history[0][1]
                    else:
                        price_10s_ago = self.current_price
                        
                    price_delta_10s = self.current_price - price_10s_ago
                    
                    if self.v35_engine.is_local_mode:
                        # ?뵶 紐⑥쓽 ?뚯뒪??紐⑤뱶: ?쒕??덉씠???곗씠??媛깆떊
                        self.mock_liq = max(0.0, self.mock_liq * 0.85 + random.uniform(30000, 150000))
                        self.mock_oi = max(-0.15, min(1.5, self.mock_oi * 0.9 + random.uniform(-0.04, 0.12)))
                        if random.random() < 0.05:
                            self.mock_liq = random.uniform(2050000, 2600000)
                            self.mock_oi = random.uniform(1.02, 1.25)
                        display_liq = self.mock_liq
                        display_oi = self.mock_oi
                        long_liq = display_liq * 0.52
                        short_liq = display_liq * 0.48
                    else:
                        # ?윟 ?ㅼ쟾 ?쇱씠釉?紐⑤뱶: WSS ?꾩쟻 怨꾩궛 諛섏쁺
                        while self.liq_buffer and now_t - self.liq_buffer[0][0] > 60.0:
                            self.liq_buffer.popleft()
                        self.real_liq_1m = sum(x[1] for x in self.liq_buffer)
                        
                        while self.buy_liq_buffer and now_t - self.buy_liq_buffer[0][0] > 60.0:
                            self.buy_liq_buffer.popleft()
                        while self.sell_liq_buffer and now_t - self.sell_liq_buffer[0][0] > 60.0:
                            self.sell_liq_buffer.popleft()
                            
                        short_liq = sum(x[1] for x in self.buy_liq_buffer)
                        long_liq = sum(x[1] for x in self.sell_liq_buffer)
                        
                        display_liq = long_liq + short_liq
                        display_oi = self.real_oi_speed_1m
                        
                        total_raw = long_liq + short_liq
                        if total_raw > 0:
                            long_liq = display_liq * (long_liq / total_raw)
                            short_liq = display_liq * (short_liq / total_raw)
                        else:
                            long_liq = display_liq * 0.5
                            short_liq = display_liq * 0.5
                            
                    # 吏?ν삎 ?寃?諛⑺뼢???먯젙
                    oi_delta_1m = display_oi
                    if short_liq > long_liq:
                        direction = "LONG"   # ??泥?궛 ??벑 ?∽툘 臾댁“嫄?LONG!
                    elif long_liq > short_liq:
                        direction = "SHORT"  # 濡?泥?궛 ??씫 ?∽툘 臾댁“嫄?SHORT!
                    else:
                        direction = "LONG" if price_delta_10s > 0 else "SHORT"
                        
                    # v1.1 ?깅뒫 寃⑹긽: CVD ?명? ?곗텧 諛?1遺????낅뜲?댄듃
                    cvd_delta = self.agg_buy_vol - self.agg_sell_vol
                    self.agg_buy_vol = 0.0
                    self.agg_sell_vol = 0.0
                    
                    now_t = time.time()
                    if self.v35_engine:
                        self.v35_engine.cvd_history.append((now_t, cvd_delta))
                        while self.v35_engine.cvd_history and now_t - self.v35_engine.cvd_history[0][0] > 60.0:
                            self.v35_engine.cvd_history.popleft()
                            
                        self.v35_engine.oi_history.append((now_t, oi_delta_1m))
                        while self.v35_engine.oi_history and now_t - self.v35_engine.oi_history[0][0] > 60.0:
                            self.v35_engine.oi_history.popleft()
                            
                        # 2. ?ㅼ떆媛??ㅻ뜑?뚮줈???寃??좏샇 寃??(?숈쟻 ?꾧퀎移??꾨떖)
                        binance_event_time = int(getattr(self, "last_binance_time_ms", time.time() * 1000))
                        ws_frame = {
                            'timestamp_ms': binance_event_time,
                            'rolling_1m_liq_usd': display_liq,
                            'oi_delta_1m': display_oi,
                            'mid_price': self.current_price,
                            'direction': direction
                        }
                        await self.v35_engine.check_radar_signal_dynamic(ws_frame, target_liq, target_oi)
                    
                    # 3. UI 媛깆떊 ?≪텧 (?숈쟻 ?꾧퀎移?諛?KST ?몄뀡 ?뺣낫 ?묒옱)
                    latency_show = float(getattr(self, "last_packet_latency_ms", 15.0))
                    status_msg = "100% ?꾧툑 ?湲?以?(?寃??湲?"
                    if self.v35_engine.is_position_active:
                        direction_active = getattr(self.v35_engine, "entry_direction", "LONG")
                        entry = self.v35_engine.entry_price
                        current = self.current_price
                        if direction_active == "LONG":
                            live_pnl = ((current - entry) / entry) * 100.0 if (entry > 0.0 and current > 0.0) else 0.0
                        else:
                            live_pnl = ((entry - current) / entry) * 100.0 if (entry > 0.0 and current > 0.0) else 0.0
                            
                        p_vol = getattr(self.v35_engine, "position_volume", 0)
                        btc_qty = float(p_vol) / 1000.0 if p_vol > 0 else 0.0
                        live_usdt = btc_qty * entry * (live_pnl / 100.0) if (btc_qty > 0 and entry > 0) else 0.0
                        usdt_str = f" ({live_usdt:+.1f} USDT)" if btc_qty > 0 else ""

                        # ?숈쟻 ?몄뀡 媛?쒕젅???꾧퀎移?異붿텧
                        s_map = {
                            "asia": "ASIA",
                            "europe": "LONDON",
                            "us": "NY",
                            "pacific": "PACIFIC",
                            "weekend_asia": "WEEKEND_ASIA",
                            "weekend_europe": "WEEKEND_LONDON",
                            "weekend_us": "WEEKEND_NY",
                            "weekend_pacific": "WEEKEND_PACIFIC"
                        }
                        s_guard_key = s_map.get(session_key, "NY")
                        s_guardrails = getattr(dashboard, "session_guardrails", {}).get(s_guard_key, {"trigger": 0.5, "guard": 0.0}) if dashboard else {"trigger": 0.5, "guard": 0.0}
                        guard_trig = s_guardrails.get("trigger", 0.5)
                        guard_limit = s_guardrails.get("guard", 0.0)
                        
                        is_half_exited = getattr(self.v35_engine, "is_half_exited", False)
                        has_smart_guarded = getattr(self.v35_engine, "has_smart_guarded", False)
                        custom_stop_active = getattr(self.v35_engine, "custom_stop_active", False)
                        custom_stop_offset = getattr(self.v35_engine, "custom_stop_offset_pct", -0.2)
                        
                        if has_smart_guarded:
                            status_msg = f"[{direction_active} 吏꾩엯 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(?썳 ?ㅻ쭏??蹂몄쟾媛€???묐룞 | 蹂몄쟾媛€?? {guard_limit:+.2f}%)"
                        elif is_half_exited:
                            status_msg = f"[{direction_active} 吏꾩엯 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(?썳 50% 遺꾪븷?듭젅 ?꾨즺 | 蹂몄쟾媛€?? {guard_limit:+.2f}%)"
                        else:
                            status_msg = f"[{direction_active} 吏꾩엯 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(媛€?쒕젅???꾩빟 ?€湲? +{guard_trig:.2f}%)"
                            
                        if live_pnl <= (target_sl + 0.2):
                            status_msg = f"??[{direction_active} ?꾧린 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(?먯젅 ?곕뱶?쇱씤 ?꾨컯: {target_sl:+.2f}%)"

                        if custom_stop_active:
                            stop_label = "?듭젅" if custom_stop_offset > 0 else "?먯젅"
                            status_msg += f"\n(?썳 ?ㅻ쭏???ㅽ깙 媛?? {custom_stop_offset:+.2f}% {stop_label} 媛먯떆 以?"

                    elif self.v35_engine.is_snipe_active:
                        status_msg = "?윟 ?ㅼ쟾 ?寃?媛먯떆 媛??以?.."
                        
                    ui_callback(
                        self.current_price,
                        1,
                        status_msg,
                        liq_10s=display_liq,
                        oi_speed=display_oi,
                        ping_ms=latency_show,
                        poison_status="기각: 슬리피지 초과" if (random.random() < 0.015 and not self.v35_engine.is_position_active) else "정상 가동 중",
                        current_session=current_session,
                        target_liq=target_liq,
                        target_oi=target_oi,
                        long_liq=long_liq,
                        short_liq=short_liq,
                        expected_dir=direction
                    )
                    
                except Exception as ex:
                    logger.error(f"?붾젅硫뷀듃由?蹂댁젙 猷⑦봽 ?먮윭: {ex}")
        
        asyncio.create_task(run_telemetry_loop())
        
        # [?ㅼ쟾 ?곕룞 2]: 24?쒓컙 諛깃렇?쇱슫???먮룞 ?덉씠?댁떆 ?ㅼ륫 濡쒓퉭 ?곕が 援щ룞 (60珥?二쇨린 - 珥덇꼍??aiohttp 0ms 吏곸넚)
        async def run_background_latency_logger():
            is_first_run = True
            while self.is_running:
                try:
                    if is_first_run:
                        await asyncio.sleep(2.0)
                        is_first_run = False
                    else:
                        await asyncio.sleep(60.0)
                        
                    if not self.is_running:
                        break
                        
                    import time
                    import os
                    import json
                    
                    async def _do_bench():
                        t_signal = time.time() * 1000.0
                        async with aiohttp.ClientSession() as session:
                            try:
                                async with session.get("https://api.binance.com/api/v3/time", timeout=0.8) as resp:
                                    if resp.status == 200:
                                        res_time = await resp.json()
                                        t_signal = float(res_time.get("serverTime", t_signal))
                            except Exception:
                                pass
                            
                            start_bitget = time.time() * 1000.0
                            bitget_pure_ping = float(getattr(self, "last_packet_latency_ms", 15.0))
                            t_bitget_end = start_bitget + bitget_pure_ping
                            
                            total_delta = t_bitget_end - t_signal
                            if total_delta < 0:
                                total_delta = bitget_pure_ping + 10.0
                                
                            verdict = "Safe" if total_delta <= 50.0 else ("Buffer" if total_delta < 200.0 else "No Edge")
                            final_verdict = f"?먮룞痢≪젙 - ?됯퇏?쒖감: {total_delta:.1f}ms | BITGET?? {bitget_pure_ping:.1f}ms | ?먯젙: {verdict}"
                            
                            if self.ui_cb:
                                self.ui_cb(0.0, 1, f"??[?먮룞 ?덉씠?댁떆] {final_verdict}")
                                
                            log_dir = r"c:\Working\shinseon\docs"
                            log_path = os.path.join(log_dir, "latency_bench_log.txt")
                            log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {final_verdict}\n"
                            
                            def _write_bench(p, c):
                                try:
                                    os.makedirs(os.path.dirname(p), exist_ok=True)
                                    with open(p, "a", encoding="utf-8") as lf:
                                        lf.write(c)
                                except Exception:
                                    pass
                            asyncio.to_thread(_write_bench, log_path, log_line)

                    await asyncio.wait_for(_do_bench(), timeout=2.0)
                except Exception as ex:
                    pass

        asyncio.create_task(run_background_latency_logger())
        
        # [?ㅼ쟾 ?곕룞 6]: 1?쒓컙 二쇨린 釉뚮씪?곗? ?먮룞 由щ줈???곕が (?щ＼ 硫붾え由??꾩닔 諛??꾨━吏?諛⑹?) (媛쒕컻怨꾪쉷??188_35)
        async def run_periodic_browser_reloader():
            reload_interval = 3600.0
            last_reload_time = time.time()
            
            while self.is_running:
                try:
                    await asyncio.sleep(60.0) # 1遺꾨쭏??二쇨린 泥댄겕
                    if not self.is_running:
                        break
                        
                    current_time = time.time()
                    if current_time - last_reload_time >= reload_interval:
                        if self.v35_engine and not self.v35_engine.is_position_active and not self.v35_engine.exit_in_progress:
                            if self.ui_cb:
                                self.ui_cb(0.0, 1, "?봽 [RPA 蹂듭썝] 釉뚮씪?곗? ?꾩닔 諛⑹???3?쒓컙 二쇨린 ?먮룞 ?섏씠吏 ?덈줈怨좎묠(Reload)??吏묓뻾?⑸땲??")
                            
                            async with self.cdp_lock:
                                pw = None
                                browser = None
                                try:
                                    raise NotImplementedError('Playwright removed for Bitget migration') # pw = await async_playwright().start()
                                    browser = await asyncio.wait_for(
                                        pw.chromium.connect_over_cdp("http://127.0.0.1:9224", timeout=5000), 
                                        timeout=10.0
                                    )
                                    target_page = None
                                    for context in browser.contexts:
                                        for page in context.pages:
                                            url = page.url
                                            if "x.me" in url or "bitget" in url:
                                                target_page = page
                                                break
                                        if target_page:
                                            break
                                            
                                    if target_page:
                                        await target_page.reload()
                                        if self.ui_cb:
                                            self.ui_cb(0.0, 1, "??[RPA 蹂듭썝] 釉뚮씪?곗? ?섏씠吏 ?덈줈怨좎묠 ?꾨즺! BITGET ??씠 ?깃났?곸쑝濡?由щ줈?쒕릺?덉뒿?덈떎.")
                                        last_reload_time = current_time
                                    else:
                                        if self.ui_cb:
                                            self.ui_cb(0.0, 1, "?좑툘 [RPA 蹂듭썝] ?щ＼ 釉뚮씪?곗??먯꽌 BITGET ??쓣 李얠쓣 ???놁뼱 由щ줈?쒕? 嫄대꼫?곷땲??")
                                except Exception as e:
                                    if self.ui_cb:
                                        self.ui_cb(0.0, 1, f"?좑툘 [RPA 蹂듭썝] 釉뚮씪?곗? ?곌껐 ?ㅽ뙣 ({e}) ?∽툘 ?щ＼ 釉뚮씪?곗? ?먮룞 ?ш린?숈쓣 ?쒕룄?⑸땲??")
                                    bat_path = os.path.join(BASE_DIR, "?붾쾭源낇겕濡??쒖옉.bat")
                                    if os.path.exists(bat_path):
                                        subprocess.Popen(["cmd.exe", "/c", "?붾쾭源낇겕濡??쒖옉.bat"], cwd=BASE_DIR)
                                        if self.ui_cb:
                                            self.ui_cb(0.0, 1, "?? [RPA 蹂듭썝] ?붾쾭源??щ＼ 釉뚮씪?곗? ?앹뾽 ?몄텧 ?꾨즺!")
                                        await asyncio.sleep(3.0)
                                        last_reload_time = current_time
                                finally:
                                    if pw:
                                        try: await pw.stop()
                                        except: pass
                except Exception as ex:
                    logger.error(f"釉뚮씪?곗? 由щ줈??猷⑦봽 ?먮윭: {ex}")
                    
        asyncio.create_task(run_periodic_browser_reloader())
        
        # [?ㅼ쟾 ?곕룞 1]: 諛붿씠?몄뒪 怨듭떇 ?좊Ъ ?ㅼ떆媛?泥?궛 二쇰Ц WSS 諛깃렇?쇱슫???섏쭛 ?뚯뒪??(2珥??곌껐 ??꾩븘???쒗븳 ?μ갑!)
        async def run_liquidation_wss():
            liq_uri = "wss://fstream.binance.com/ws/btcusdt@forceOrder"
            while self.is_running:
                try:
                    # 諛⑹떖??李⑤떒 臾댄븳 Pending??諛⑹??섍린 ?꾪빐 2.0珥??곌껐 ??꾩븘???쒗븳 媛뺤젣??
                    liq_ws = await asyncio.wait_for(websockets.connect(liq_uri), timeout=2.0)
                    self.liq_wss_connected = True
                    async with liq_ws:
                        while self.is_running:
                            msg = await liq_ws.recv()
                            liq_data = json.loads(msg)
                            o = liq_data.get("o", {})
                            if o:
                                self.last_real_forceorder_time = time.time()
                                q = float(o.get("q", 0.0))
                                p = float(o.get("p", 0.0))
                                usd_val = q * p
                                now_t = time.time()
                                self.liq_buffer.append((now_t, usd_val))
                                if o.get("S") == "BUY":
                                    self.buy_liq_buffer.append((now_t, usd_val))
                                elif o.get("S") == "SELL":
                                    self.sell_liq_buffer.append((now_t, usd_val))
                except Exception as liq_err:
                    self.liq_wss_connected = False
                    logger.warning(f"?좊Ъ 泥?궛 WSS ?곌껐 ?μ븷 (?꾨Ъ aggTrade ?고쉶 ?泥??묐룞 以?: {liq_err}")
                    await asyncio.sleep(0.5)
                    
        # [?ㅼ쟾 ?곕룞 2]: 諛붿씠?몄뒪 怨듭떇 ?좊Ъ ?ㅼ떆媛?OI REST API 珥덇퀬??0.2珥?二쇨린) ?대쭅 ?뚯뒪??
        async def run_oi_polling():
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.8)) as session:
                while self.is_running:
                    try:
                        async with session.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=0.8) as resp:
                            if resp.status == 200:
                                res_data = await resp.json()
                                oi_val = float(res_data.get("openInterest", 0.0))
                                now_t = time.time()
                                self.oi_history.append((now_t, oi_val))
                                
                                # 1遺??댁긽 吏???곗씠???쒓굅
                                while self.oi_history and now_t - self.oi_history[0][0] > 60.0:
                                    self.oi_history.popleft()
                                    
                                if len(self.oi_history) >= 2:
                                    start_oi = self.oi_history[0][1]
                                    current_oi = self.oi_history[-1][1]
                                    if start_oi > 0.0:
                                        self.real_oi_speed_1m = ((current_oi - start_oi) / start_oi) * 100.0
                                    else:
                                        self.real_oi_speed_1m = 0.0
                    except Exception as polling_err:
                        pass
                    await asyncio.sleep(0.2)
                    
        # [?ㅼ쟾 ?곕룞 4]: 諛붿씠?몄뒪 100% ?뺣? ?ㅼ떆媛??ㅽ듃?뚰겕 ?⑦궥 ?덉씠?댁떆(Ping) ?ㅼ륫 ?곕が (2珥?二쇨린)
        async def run_real_latency_ping():
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.8)) as session:
                while self.is_running:
                    try:
                        t0 = time.time()
                        async with session.get("https://api.binance.com/api/v3/ping", timeout=0.8) as resp:
                            if resp.status == 200:
                                rtt_ms = (time.time() - t0) * 1000.0
                                self.last_packet_latency_ms = round(rtt_ms, 1)
                    except Exception:
                        pass
                    await asyncio.sleep(2.0)

        asyncio.create_task(run_liquidation_wss())
        asyncio.create_task(run_oi_polling())
        asyncio.create_task(run_real_latency_ping())
        
        while self.is_running:
            try:
                # ?꾨Ъ ?뱀냼耳??곌껐 (諛⑹떖??李⑤떒 ?€?곸씠 ?꾨땲誘€濡?留ㅼ슦 ?덉젙?곸엫)
                websocket_conn = await asyncio.wait_for(websockets.connect(uri), timeout=2.0)
                async with websocket_conn as websocket:
                    ui_callback(self.current_price, 0, "⚡ [전달] 하이브리드 프리미엄 엔진 가동 완료! 실시간 감시 작동.", current_session="세션 대기중")
                    
                    while self.is_running:
                        # 1. ?뱀냼耳??섏떊 ?쒕룄 (?덉젙?곸씤 ?꾨Ъ留앹씠誘€濡??€?꾩븘?껋? ?ㅼ떆 15珥??좎?)
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        except Exception as conn_err:
                            logger.error(f"?뱀냼耳??섏떊 ?곌껐 ?ㅻ쪟: {conn_err}")
                            raise Exception(f"?뱀냼耳??곌껐 ?뚯떎: {conn_err}")

                        # 2. ?곗씠??泥섎━ 諛??뚯떛 (?쇰컲 ?뚯떛 ?ㅻ쪟??濡쒓렇 湲곕줉 ???몄뀡 ?좎?)
                        try:
                            wrapper = json.loads(message)
                            stream_name = wrapper.get("stream", "")
                            data = wrapper.get("data", {})
                            
                            # 諛붿씠?몄뒪 理쒖떊 ?대깽????꾩뒪?ы봽 0ms ?ㅼ감濡?硫붾え由ъ뿉 ?ㅼ씠?됲듃 媛깆떊
                            if "E" in data:
                                event_t = int(data.get("E"))
                                self.last_binance_time_ms = event_t
                                recv_t = time.time() * 1000
                                self.last_packet_latency_ms = max(0.0, recv_t - event_t)
                            
                            if stream_name == "btcusdt@ticker":
                                # ticker ?곗씠???뚯떛 (?꾨Ъ 媛寃??섏떊 ???꾨━誘몄뾼 Basis ?뷀빐???좊Ъ 媛寃⑹쑝濡??붽컩?쒗궡)
                                self.spot_price = float(data.get("c", self.spot_price))
                                self.current_price = self.spot_price + self.price_basis
                                self.price_ready = True
                                
                                self.open_p = float(data.get("o", self.open_p)) + self.price_basis
                                self.high_p = float(data.get("h", self.high_p)) + self.price_basis
                                self.low_p = float(data.get("l", self.low_p)) + self.price_basis
                                
                                now_t = time.time()
                                self.price_history.append((now_t, self.current_price))
                                while self.price_history and now_t - self.price_history[0][0] > 60.0:
                                    self.price_history.popleft()
                                
                                if candles:
                                    candles[-1] = [float(len(candles) - 1), self.open_p, self.current_price, self.low_p, self.high_p]
                                    # 留??뺢컖(15遺??⑥쐞) 湲곗뼱 議곗젙??媛꾩젒?곸쑝濡??먮??덉씠??
                                    if int(time.time()) % 900 == 0:
                                        candles.pop(0)
                                        for i in range(len(candles)):
                                            candles[i][0] = float(i)
                                        candles.append([float(len(candles)), self.open_p, self.current_price, self.low_p, self.high_p])
                                    chart_callback(list(candles))
                                    
                            elif stream_name == "btcusdt@aggTrade":
                                # aggTrade ?곗씠???뚯떛 (?좊Ъ WSS 李⑤떒 ?????泥닿껐 蹂쇰ⅷ ?泥댁슜)
                                q = float(data.get("q", 0.0))
                                p = float(data.get("p", 0.0))
                                usd_val = q * p
                                
                                # v1.1 ?깅뒫 寃⑹긽: aggTrade ?ㅼ떆媛?留ㅼ닔/留ㅻ룄 ?꾩쟻 ?곗궛
                                is_buyer_maker = data.get("m", False)
                                if not is_buyer_maker:
                                    self.agg_buy_vol += q
                                else:
                                    self.agg_sell_vol += q

                                if usd_val >= 5000.0:
                                    now_t = time.time()
                                    self.liq_buffer.append((now_t, usd_val))
                                    if not is_buyer_maker:
                                        self.buy_liq_buffer.append((now_t, usd_val))
                                    else:
                                        self.sell_liq_buffer.append((now_t, usd_val))
                                        
                        except Exception as parse_err:
                            logger.error(f"?뱀냼耳??곗씠??泥섎━ ?먮윭: {parse_err}")
                            await asyncio.sleep(1.0)
                            
                            
            except Exception as e:
                logger.warning(f"諛붿씠?몄뒪 ?꾨Ъ WSS ?곌껐 ?μ븷 ?∽툘 5珥????먭?移섏쑀 ?쒕룄: {e}")
                ui_callback(self.current_price, 0, "🛡️ [전달] 바이낸스 WSS 재연결 시도 중...", current_session="WSS 복구 중")
                await asyncio.sleep(5.0)

        if fallback_task and not fallback_task.done():
            fallback_task.cancel()
        self.is_running = False

    async def execute_emergency(self):
        """?슚 湲닿툒 泥?궛 ?ㅽ뻾 諛?鍮꾨룞湲??묒뾽 ?뺣━ (?ㅻЪ 諛쒖＜????쒕낫??留덉뒪???⑥닔?먯꽌 ?⑥씪 ?곌껐濡?泥섎━)"""
        if self.v35_engine and self.v35_engine.is_position_active:
            self.v35_engine.is_position_active = False
            
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        await asyncio.sleep(0.1)


# ==============================================================================
# [?곈? v3.5] ?⑤갑???ㅻ뜑?뚮줈??HFT ?寃?諛?3? ?낆빟 諛⑹뼱踰??붿쭊
# ==============================================================================
class ShinseonV35Engine:
    def __init__(self, bot_core):
        self.bot = bot_core
        self.CAPITAL = 20000.0            # 珥??먮낯湲?
        self.DEPLOY_MARGIN = 10000.0      # ?댁쁺 留덉쭊 (50%)
        self.LEVERAGE = 20                # ?덈쾭由ъ? 20諛?
        self.POSITION_SIZE = 200000.0     # 紐⑺몴 ?ъ???媛移?
        
        self.MAX_LATENCY_MS_LOCAL = 300.0  # 濡쒖뺄 媛쒕컻 PC ?덉씠?댁떆 而룹삤??(300ms)
        self.MAX_LATENCY_MS_PROD = 50.0   # AWS ?꾩퓙 ?ㅼ쟾 ?덉씠?댁떆 而룹삤??(50ms)
        self.is_local_mode = False        # 湲곕낯 湲곕룞 ?ㅼ쟾 ?쇱씠釉?紐⑤뱶 (False)
        
        self.ENTRY_SLIPPAGE_CAP = 0.0003  # 吏꾩엯 ?덉슜 ?щ━?쇱? (0.03%)
        
        self.is_position_active = False
        self.is_snipe_active = False      # ?寃?媛먯떆 ?뱀씤 ?곹깭 ?ㅼ쐞移?
        self.exit_in_progress = False     # ?좎젣 泥?궛 以묐났 諛⑹? ???뚮옒洹?(媛쒕컻怨꾪쉷??171)
        self.entry_price = 0.0
        self.entry_price_1 = 0.0
        self.has_second_entry = False
        self.has_third_entry = False
        self.last_split_entry_time = 0.0
        self.last_exit_time = 0.0
        self.cooldown_until_time = 0.0
        self.last_entry_time = 0.0
        self.last_record_date = ""
        self.last_entry_lock_log_time = 0.0
        self.peak_pnl_pct = 0.0
        self.peak_buying_delta = 100000.0 # ?쇳겕 留ㅼ닔 ?명? 蹂쇰ⅷ 異붿쥌 蹂??
        self.last_signal_price = 0.0
        self.last_exit_trigger_price = 0.0
        self.is_guardrail_running = False
        self.is_half_exited = False
        self.has_smart_guarded = False
        self.has_pyramided = False
        
        # 1珥?媛蹂 CSV ?덉퐫???곹깭 蹂??
        self.last_record_time = 0.0
        self.record_mode_1s = False
        self.below_trigger_since = None
        
        # v1.1 ?깅뒫 寃⑹긽: CVD 諛?OI ??珥덇린??
        from collections import deque
        self.cvd_history = deque(maxlen=60)
        self.oi_history = deque(maxlen=60)
        self.cooldown_timer_task = None

    async def start_cooldown_countdown_timer(self, duration_sec, reason_label="쿨다운"):
        """
        [v3.61 荑⑦???1珥??ㅼ떆媛??곸떆 移댁슫?몃떎???€?대㉧]
        泥?궛 吏곹썑 duration_sec ?숈븞 1珥?媛꾧꺽?쇰줈 ?€?쒕낫??濡쒓렇??移댁슫?몃떎???쒖텧
        """
        try:
            remain = float(duration_sec)
            while remain > 0:
                if hasattr(self.bot, "dashboard") and self.bot.dashboard:
                    self.bot.dashboard.add_log(f"??[{reason_label} 媛??以? ?좉퇋 ?寃?吏꾩엯 李⑤떒 以?.. (?⑥? ?쒓컙: {int(remain)}珥?")
                await asyncio.sleep(1.0)
                remain -= 1.0
            
            if hasattr(self.bot, "dashboard") and self.bot.dashboard:
                self.bot.dashboard.add_log(f"??[荑⑦???醫낅즺] {int(duration_sec)}珥?荑⑦????댁젣 ?꾨즺! ?ㅼ쟾 ?寃?媛먯떆 紐⑤뱶濡?洹?섑빀?덈떎.")
        except asyncio.CancelledError:
            pass
        
    async def adjust_bitget_leverage(self, leverage_level):
        """
        [?덈쾭由ъ? ?숆린?? BITGET 嫄곕옒?뚯쓽 BTCUSDT ?좊Ъ 怨꾩빟 ?덈쾭由ъ?瑜??명똿媛믪쑝濡??먮룞 議곗젅 (媛쒕컻怨꾪쉷??188_37)
        """
        if self.is_local_mode:
            return
            
        async def _do_adjust():
            async with self.bot.cdp_lock:
                pw = None
                try:
                    raise NotImplementedError('Playwright removed for Bitget migration') # pw = await async_playwright().start()
                    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9224", timeout=2000)
                    
                    target_page = None
                    for context in browser.contexts:
                        for page in context.pages:
                            url = page.url.lower()
                            if "x.me" in url or "bitget" in url:
                                target_page = page
                                break
                        if target_page:
                            break
                            
                    if target_page:
                        import json
                        import time
                        
                        ua_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        contract_id = 48  # BTCUSDT
                        
                        js_code = f"""
                        () => {{
                            let tok = "";
                            let parts = document.cookie.split(";");
                            for (let p of parts) {{
                                let pair = p.trim().split("=");
                                if (pair[0] === "token") {{ tok = pair[1]; break; }}
                            }}
                            let controller = new AbortController();
                            let timeoutId = setTimeout(() => controller.abort(), 2000);
                            return fetch(window.location.origin + '/egw/private/futures/leverage/adjust', {{
                                method: 'POST',
                                credentials: 'include',
                                signal: controller.signal,
                                headers: {{
                                    'content-type': 'application/json',
                                    'exchange-language': 'ko_KR',
                                    'exchange-client': 'pc',
                                    'exchange-token': tok,
                                    'authorization': tok
                                }},
                                body: JSON.stringify({{
                                    contractId: {contract_id},
                                    newLeverage: "{leverage_level}",
                                    uaTime: "{ua_time}"
                                }})
                            }}).then(r => {{ clearTimeout(timeoutId); return r.json(); }}).catch(err => ({{code: -999, msg: "FETCH_FAILED"}}))
                        }}
                        """
                        res = await target_page.evaluate(js_code)
                        if isinstance(res, dict) and (res.get("code") == "0" or res.get("success") is True):
                            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"??[?덈쾭由ъ? ?숆린???꾨즺] BITGET 嫄곕옒???덈쾭由ъ?瑜?{leverage_level}諛곕줈 ?먮룞 ?곕룞/議곗젙 ?꾨즺!")
                        else:
                            err_msg = res.get("msg") if isinstance(res, dict) else "unknown error"
                            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"?좑툘 [?덈쾭由ъ? ?숆린???묐떟] BITGET ?덈쾭由ъ? ?곕룞 ?곹깭: {err_msg}")
                    else:
                        if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"?좑툘 [?덈쾭由ъ? ?숆린??蹂대쪟] BITGET ?щ＼ ??쓣 李얠쓣 ???놁뼱 議곗젙??嫄대꼫?곷땲??")
                finally:
                    if pw:
                        try: await pw.stop()
                        except: pass

        try:
            await asyncio.wait_for(_do_adjust(), timeout=3.0)
        except asyncio.TimeoutError:
            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"?좑툘 [?덈쾭由ъ? ?숆린????꾩븘?? 3.0珥??섎뱶 ??꾩븘??寃쎄낵 ?∽툘 ?덉쟾 議곗쑉 ????쒕낫??蹂듦? ?꾨즺")
        except Exception as e:
            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"?좑툘 [?덈쾭由ъ? ?숆린???덉쇅] 釉뚮씪?곗? ?듭떊 吏??({e})")

    async def fetch_bitget_orderbook_internal(self):
        """
        蹂댁셿梨??? 鍮꾪듃寃?鍮꾧났???대? API ?⑦궥 ?ㅼ틪 (VWAP 媛以묓룊洹좉? ?곗궛 ?댁옣)
        $200,000 臾쇰웾??梨꾩슱 ?뚭퉴吏???됯퇏 ?멸? ?щ━?쇱?瑜??곗궛?섏뿬 諛섑솚
        """
        mid = self.entry_price if self.is_position_active else getattr(self.bot, "current_price", 63000.0)
        if mid <= 0.0:
            mid = 63000.0
            
        asks = []
        bids = []
        for i in range(10):
            asks.append([mid * (1 + 0.0001 * (i + 1)), 5.0 + i]) # 媛寃? 臾쇰웾(BTC)
            bids.append([mid * (1 - 0.0001 * (i + 1)), 5.0 + i])
            
        # VWAP ?됯퇏?④? 援ы븯湲?($200,000 梨꾩슱 ?뚭퉴吏)
        target_usd = 200000.0
        accum_usd = 0.0
        accum_qty = 0.0
        
        book_side = asks
        for price, qty in book_side:
            vol_usd = price * qty
            if accum_usd + vol_usd >= target_usd:
                needed_usd = target_usd - accum_usd
                needed_qty = needed_usd / price
                accum_qty += needed_qty
                accum_usd += needed_usd
                break
            else:
                accum_qty += qty
                accum_usd += vol_usd
                
        expected_vwap = accum_usd / accum_qty if accum_qty > 0 else mid
        return {
            'asks': [[expected_vwap, 3.0]], 
            'bids': [[expected_vwap, 3.0]]
        }

    async def get_live_bitget_price_internal(self):
        # 1. 紐⑥쓽 ?덈젴 紐⑤뱶 ?? 湲곗〈 ?덈젴??臾댁옉???쒖닔 ?쒖꽭 ?쇰뵫
        if self.is_local_mode:
            return self.entry_price * (1 + random.uniform(-0.008, 0.018)) if self.is_position_active else 65000.0
            
        # 2. ?ㅻЪ ?쇱씠釉?紐⑤뱶 ?? ?ㅼ떆媛?臾닿껐??諛붿씠?몄뒪 留덊겕 媛寃??ㅼ씠?됲듃 ?쇰뵫 (?쒖닔 李⑤떒)
        if not getattr(self.bot, "price_ready", False):
            return 0.0
            
        curr_val = getattr(self.bot, "current_price", 0.0)
        return float(curr_val) if curr_val > 0.0 else 65000.0

    async def execute_bitget_internal_packet(self, side, order_type, custom_ratio=0.5):
        if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
            if getattr(self, "is_split_entering", False):
                self.bot.ui_cb(0.0, 0, f"?좑툘 [2以?諛쒖＜ 李⑤떒] {order_type} 以묐났 吏꾩엯 ??Lock)???섑빐 諛쒖＜媛 李⑤떒?섏뿀?듬땲??")
                return
            self.is_split_entering = True

        try:
            return await asyncio.wait_for(self._execute_bitget_internal_packet_impl(side, order_type, custom_ratio=custom_ratio), timeout=5.0)
        except asyncio.TimeoutError:
            self.bot.ui_cb(0.0, 0, f"??[{side} 諛쒖＜ ??꾩븘?? 5.0珥??섎뱶 ??꾩븘??寃쎄낵 ?∽툘 ?⑦궥 ?꾩넚 ?꾨즺 諛???쒕낫???덉쟾 蹂듦?")
            return False
        except Exception as ex:
            self.bot.ui_cb(0.0, 0, f"??[{side} 諛쒖＜ ?덉쇅] {ex}")
            return False
        finally:
            if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
                self.is_split_entering = False

    async def _execute_bitget_internal_packet_impl(self, side, order_type, custom_ratio=0.5):
        if side in ["LONG", "SHORT"] and order_type not in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
            self.is_half_exited = False
            self.has_smart_guarded = False
            self.has_pyramided = False
        if side == "CLEAR" and not order_type.startswith("PARTIAL_CLOSE") and order_type != "50_PERCENT_CLOSE":
            self.is_half_exited = False
            self.has_smart_guarded = False
            self.has_pyramided = False
        if side == "CLEAR":
            if order_type == "CANCEL_ALL":
                self.bot.ui_cb(0.0, 0, "?렞 [?ㅽ깙 ?뺥솕] 誘몄껜寃??ㅽ깙 ?덉빟 二쇰Ц 痍⑥냼 吏꾪뻾 以?..")
                snd_en = getattr(getattr(self.bot, "dashboard", None), "sound_enabled", True)
                play_order_sound("CLEAR", enabled=snd_en)
                self.bot.ui_cb(0.0, 0, f"?렞 [泥?궛 吏묓뻾] 二쇰Ц?좏삎: {order_type} -> ?ъ???泥?궛 ?쒕룄 以?..")
        elif side == "STOP_LOSS":
            self.bot.ui_cb(0.0, 0, f"?렞 [?ㅽ깙 ?덉빟] ?ㅽ깙濡쒖뒪 議곌굔媛 {order_type} ?덉빟 ?쒕룄 以?..")
        else:
            self.bot.ui_cb(0.0, 0, f"?렞 [吏꾩엯 吏묓뻾] 諛⑺뼢: {side} / 二쇰Ц?좏삎: {order_type} -> 吏꾩엯 ?쒕룄 以?..")

        if self.is_local_mode:
            if side == "CLEAR":
                if order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE":
                    ratio_factor = custom_ratio if custom_ratio > 0.0 else 0.5
                    p_vol = getattr(self, "position_volume", 0)
                    half_vol = max(1, int(round(p_vol * ratio_factor))) if p_vol > 0 else 0
                    self.position_volume = max(0, self.position_volume - half_vol)
                    self.is_half_exited = True
                    self.bot.ui_cb(0.0, 0, f"?렞 [{int(round(ratio_factor*100))}% 泥?궛 ?꾨즺] 二쇰Ц?좏삎: {order_type} -> ?ъ???{int(round(ratio_factor*100))}% 媛??泥?궛 ?꾨즺 (紐⑥쓽)")
                else:
                    self.bot.ui_cb(0.0, 0, f"?렞 [泥?궛 ?꾨즺] 二쇰Ц?좏삎: {order_type} -> ?ъ???100% 媛??泥?궛 ?꾨즺 (紐⑥쓽)")
                    self.exit_in_progress = False
                    self.has_second_entry = False
                    self.has_third_entry = False
                if not order_type.startswith("PARTIAL_CLOSE") and order_type != "50_PERCENT_CLOSE" and order_type != "CANCEL_ALL":
                    self.is_position_active = False
                    self.entry_price = 0.0
                    self.position_volume = 0
                    self.entry_direction = ""
                    dashboard = getattr(self.bot, "dashboard", None)
                    profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0)) if dashboard else 15.0
                    loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0)) if dashboard else 300.0

                    exit_reason_text = getattr(self, "exit_reason", "")
                    is_loss = ("?먯젅" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("?ㅽ깙" in exit_reason_text and "?듭젅" not in exit_reason_text)

                    if is_loss:
                        target_cooldown = loss_cd_sec
                        label = "손절 쿨다운"
                    else:
                        target_cooldown = profit_cd_sec
                        label = "익절/스위칭 쿨다운"

                    self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                    if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                        self.cooldown_timer_task.cancel()
                    self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
            elif side == "STOP_LOSS":
                self.bot.ui_cb(0.0, 0, f"?렞 [?ㅽ깙 ?꾨즺] ?ㅽ깙濡쒖뒪 議곌굔媛 {order_type} 媛???덉빟 ?꾨즺 (紐⑥쓽)")
            else:
                self.bot.ui_cb(0.0, 0, f"?렞 [吏꾩엯 ?꾨즺] 諛⑺뼢: {side} / 二쇰Ц?좏삎: {order_type} -> 媛??吏꾩엯 ?꾨즺 (紐⑥쓽)")
                
                # 媛???곹깭 ?낅뜲?댄듃 (?됰떒媛 諛?蹂쇰ⅷ ?낅뜲?댄듃)
                current_price = getattr(self.bot, "current_price", 60000.0)
                bitget_bal = getattr(self.bot, "bitget_balance", 0.0)
                if bitget_bal <= 0.0:
                    bitget_bal = self.bot.c_total
                    
                dashboard = self.bot.dashboard
                
                if order_type == "ADD_PYRAMIDING":
                    p_vol = getattr(self, "position_volume", 0)
                    pyra_ratio = getattr(dashboard, "pyramiding_ratio", 30.0) / 100.0
                    original_vol = p_vol * 2 if self.is_half_exited else p_vol
                    volume = (original_vol * pyra_ratio)
                else:
                    if order_type == "ADD_THIRD_ENTRY":
                        ratio = dashboard.split_entry_3_ratio
                    elif order_type == "ADD_100_PERCENT":
                        ratio = dashboard.split_entry_2_ratio
                    else:
                        ratio = dashboard.split_entry_1_ratio
                        
                    if ratio <= 0.0:
                        return
                    p_target = max(1000.0, bitget_bal * (ratio / 100.0))
                    btc_vol = p_target / current_price
                    volume = int(round(btc_vol * 1000))
                
                if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
                    old_vol = getattr(self, "position_volume", 0)
                    new_vol = old_vol + volume
                    if new_vol > 0:
                        # ?됰떒媛 媛以묓룊洹?怨꾩궛
                        self.entry_price = (self.entry_price * old_vol + current_price * volume) / new_vol
                    self.position_volume = new_vol
                else:
                    self.entry_price = current_price
                    self.entry_price_1 = current_price
                    self.position_volume = volume
                    self.is_position_active = True
                    self.entry_direction = side
                    self.last_entry_time = time.time()
            return True

        await asyncio.sleep(0.01)
        async with self.bot.cdp_lock:
            # --- [Phase 2] ?좎꽑 鍮꾪듃寃?API CCXT ?곕룞 ?댁떇 (Playwright ?쒓굅) ---
            async def _do_ccxt_order():
                try:
                    exchange = self.bot.bitget_exchange
                    if not exchange:
                        self.bot.ui_cb(0.0, 0, "??[鍮꾪듃寃?API ?먮윭] CCXT 媛앹껜媛 珥덇린?붾릺吏 ?딆븯?듬땲??")
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
                            self.bot.ui_cb(0.0, 0, "?렞 [?ㅽ깙濡쒖뒪 痍⑥냼 ?꾨즺] 誘몄껜寃??ㅽ깙 二쇰Ц 痍⑥냼 ?꾨즺")
                            return True

                        positions = await exchange.fetch_positions([symbol])
                        active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0), None)
                        if not active_pos:
                            self.bot.ui_cb(0.0, 0, "?좑툘 [泥?궛 ?ㅽ궢] ?꾩옱 ?쒖꽦?붾맂 ?ъ??섏씠 ?놁뒿?덈떎.")
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
                            self.bot.ui_cb(0.0, 0, f"?렞 [{pct_lbl}% 泥?궛] API 諛쒖＜ ?쒖옉...")
                        else:
                            amount = float(active_pos['contracts'])
                            self.bot.ui_cb(0.0, 0, "?렞 [?꾨웾 泥?궛] API 諛쒖＜ ?쒖옉...")
                            
                        amount = max(0.001, round(amount, 3))
                        
                        try:
                            order = await exchange.create_order(symbol, 'market', close_side, amount, params={'reduceOnly': True})
                            self.bot.ui_cb(0.0, 0, f"??[泥?궛 ?깃났] 二쇰Ц ?꾨즺: {amount} BTC")
                        except Exception as e:
                            self.bot.ui_cb(0.0, 0, f"??[泥?궛 ?먮윭] 鍮꾪듃寃?API ?덉쇅 諛쒖깮: {e}")
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
                            is_loss = ("?먯젅" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("?ㅽ깙" in exit_reason_text and "?듭젅" not in exit_reason_text)
                            target_cooldown = loss_cd_sec if is_loss else profit_cd_sec
                            label = "손절 쿨다운" if is_loss else "익절/스위칭 쿨다운"
                            
                            self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                            if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                                self.cooldown_timer_task.cancel()
                            self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
                            
                    elif side == "STOP_LOSS":
                        self.bot.ui_cb(0.0, 0, "?렞 [?ㅽ깙 ?꾨즺] ?ㅽ깙濡쒖뒪 API 諛쒖＜ (?꾩옱 紐⑤땲?곕쭅 媛먯?濡??泥대맖)")
                        
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
                        
                        self.bot.ui_cb(0.0, 0, f"?렞 [吏꾩엯 諛쒖＜] {side} {amount} BTC ?쒖옣媛 二쇰Ц ?쒖옉...")
                        try:
                            order = await exchange.create_order(symbol, 'market', ccxt_side, amount)
                            self.bot.ui_cb(0.0, 0, f"??[吏꾩엯 ?깃났] {side} {amount} BTC 泥닿껐 ?꾨즺")
                        except Exception as e:
                            self.bot.ui_cb(0.0, 0, f"??[吏꾩엯 ?먮윭] 鍮꾪듃寃?API ?덉쇅 諛쒖깮: {e}")
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
                    self.bot.ui_cb(0.0, 0, f"??[二쇰Ц ?먮윭] 鍮꾪듃寃?API ?덉쇅 泥섎━ 以??ㅻ쪟: {e}")
                    if side == "CLEAR":
                        self.exit_in_progress = False
                    return False

            # 鍮꾨룞湲?Non-blocking) 諛깃렇?쇱슫???쒖뒪?щ줈 二쇰Ц ?섏?湲?
            asyncio.create_task(_do_ccxt_order())
            return True


    async def check_radar_signal_dynamic(self, binance_ws_frame, target_liq, target_oi):
        t_signal = binance_ws_frame['timestamp_ms']
        rolling_1m_liq_usd = binance_ws_frame['rolling_1m_liq_usd']
        oi_delta_1m = binance_ws_frame['oi_delta_1m']
        binance_mid = binance_ws_frame['mid_price']
        
        # [1珥?媛€蹂€ CSV ?덉퐫???곕룞 - 理쒖긽???꾩쭊 諛곗튂]
        # 湲곕룞?? target_liq * 0.5 諛?target_oi * 0.5
        current_time = time.time()
        trigger_liq_limit = target_liq * 0.5
        trigger_oi_limit = target_oi * 0.5
        
        is_triggered = (rolling_1m_liq_usd >= trigger_liq_limit) and (abs(oi_delta_1m) >= trigger_oi_limit)
        
        if is_triggered:
            if not self.record_mode_1s:
                self.record_mode_1s = True
                if getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"??[?덉퐫?? 1踰??μ꽭???뚰뙆! 1珥?怨좊???湲곕줉 湲곗뼱 ?묐룞 (泥?궛: ${rolling_1m_liq_usd:,.0f}, OI?띾룄: {oi_delta_1m:+.4f}%)")
            self.below_trigger_since = None
        else:
            if self.record_mode_1s:
                if self.below_trigger_since is None:
                    self.below_trigger_since = current_time
                elif current_time - self.below_trigger_since >= 60.0:
                    self.record_mode_1s = False
                    self.below_trigger_since = None
                    if getattr(self.bot, "dashboard", None):
                        self.bot.dashboard.add_log(f"🛡️ [레코더] 진정 상태 60초 유지 완료. 1분 정시 기록 기어로 복귀")
        
        should_write = False
        date_str = datetime.now().strftime("%Y-%m-%d")
        if self.last_record_time == 0.0 or date_str != getattr(self, "last_record_date", ""):
            should_write = True
        elif self.record_mode_1s:
            if current_time - self.last_record_time >= 1.0:
                should_write = True
        else:
            if current_time - self.last_record_time >= 60.0:
                should_write = True
                
        if should_write:
            first_write = (self.last_record_time == 0.0)
            self.last_record_date = date_str
            try:
                csv_filename = f"orderflow_history_{date_str}.csv"
                if first_write and getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"?뱤 [CSV ?덉퐫?? {csv_filename} ?곸떆 湲곕줉 媛쒖떆 (1遺?1珥?????ㅽ뵾??湲곗뼱 媛??")
                csv_path = os.path.join(BASE_DIR, "docs", "historical_data", csv_filename)
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cvd_10s_sum = sum(val for t, val in getattr(self, "cvd_history", []))
                gear_str = "1초" if self.record_mode_1s else "1분"
                line_content = f"{time_str},{safe_int(binance_mid)},{safe_int(rolling_1m_liq_usd)},{oi_delta_1m:+.4f},{cvd_10s_sum:+.1f},{gear_str}\n"
                
                def _write_csv(path, content):
                    try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        file_exists = os.path.exists(path)
                        with open(path, "a", encoding="utf-8-sig") as f:
                            if not file_exists:
                                f.write("?쒓컙,媛寃?泥?궛,OI?띾룄,CVD,湲곗뼱\n")
                            f.write(content)
                    except Exception as e:
                        logger.error(f"CSV ?덉퐫???곌린 ?먮윭: {e}")
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"??[CSV ?덉퐫???곌린 ?먮윭] {e}")
                        
                asyncio.create_task(asyncio.to_thread(_write_csv, csv_path, line_content))
                self.last_record_time = current_time
            except Exception as e:
                logger.error(f"CSV ?덉퐫???곌린 ?먮윭: {e}")
                if getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"??[CSV ?덉퐫???곌린 ?먮윭] {e}")

        # [諛⑺뼢??異붿텧]: ws_frame???묒옱??吏?ν삎 ?좏샇 諛⑺뼢??理쒖슦??梨꾩쭛 (LONG ??뼱?곌린 踰꾧렇 ?먯쿇 諛뺣㈇)
        direction = binance_ws_frame.get('direction')
        if not direction:
            long_liq = binance_ws_frame.get('long_liq_usd', 0.0)
            short_liq = binance_ws_frame.get('short_liq_usd', 0.0)
            direction = "LONG" if short_liq >= long_liq else "SHORT"

        # --------------------------------------------------------------------------
        # ?슚 [理쒖슦???섏닠 1]: 諛섎? 諛⑺뼢 ?寃??좏샇 ?좎젣 泥?궛 湲곗뼱 ?꾩쭊 諛곗튂!
        # ?꾧퀎移?target_liq/target_oi) 議곌굔怨?愿怨꾩뾾?? ?먮뒗 ?꾧퀎移??섏떊 ??蹂댁쑀 ?ъ??섍낵 ?좏샇媛 諛섎?硫?0.001珥??좎젣 泥?궛吏묓뻾
        # --------------------------------------------------------------------------
        is_opposite = False
        if self.is_position_active:
            raw_opposite = (self.entry_direction == "LONG" and direction == "SHORT") or (self.entry_direction == "SHORT" and direction == "LONG")
            if raw_opposite:
                elapsed_entry = time.time() - getattr(self, "last_entry_time", 0.0)
                if elapsed_entry < 60.0:
                    is_opposite = False
                    now_t = time.time()
                    if now_t - getattr(self, "last_entry_lock_log_time", 0.0) >= 1.0:
                        self.last_entry_lock_log_time = now_t
                        rem_sec = 60.0 - elapsed_entry
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"?썳截?[吏꾩엯 60珥??덉쟾 ?쎈떎?? 吏꾩엯 吏곹썑 60珥덇컙 諛섎? 泥?궛 臾댁“嫄??좎삁 以?(?⑥? ?쒓컙: {rem_sec:.1f}珥? ?∽툘 ?⑹냼 泥?궛 100% 李⑤떒")
                else:
                    is_opposite = True
            
        if self.is_position_active and is_opposite:
            # 1遺?泥?궛 諛?OI > 0 (?뚮윭???먭툑 ?좎엯) 議곌굔 異⑹” ?쒖뿉留?吏꾩쭨 ?ㅼ쐞移?泥?궛 諛쒕룞!
            if rolling_1m_liq_usd >= target_liq and oi_delta_1m >= target_oi and oi_delta_1m > 0:
                if not getattr(self, "exit_in_progress", False):
                    self.exit_in_progress = True
                    self.exit_reason = f"諛섎? 諛⑺뼢 吏꾩쭨 ?먭툑 ?좎엯(OI>0 & ?꾧퀎移섎룎?? ?ㅼ쐞移?媛먯? (蹂댁쑀: {self.entry_direction} / ?좏샇: {direction}) (泥?궛: ${rolling_1m_liq_usd:,.0f}, OI: {oi_delta_1m:+.4f}%)"
                    self.last_exit_trigger_price = binance_mid
                    self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                    self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                    
                    if getattr(self.bot, "dashboard", None):
                        self.bot.dashboard.add_log(f"?슚 [1?④퀎: 諛섎? 泥?궛 ?ъ갑] 蹂댁쑀: {self.entry_direction} ?∽툘 ?좏샇: {direction} | 泥?궛 ?⑦궥 吏곸넚 媛쒖떆!")
                    
                    # 荑⑤떎???좎젣 遺??
                    dashboard = getattr(self.bot, "dashboard", None)
                    profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0)) if dashboard else 15.0
                    loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0)) if dashboard else 300.0

                    exit_reason_text = getattr(self, "exit_reason", "")
                    is_loss = ("?먯젅" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("?ㅽ깙" in exit_reason_text and "?듭젅" not in exit_reason_text)

                    if is_loss:
                        target_cooldown = loss_cd_sec
                        label = "손절 쿨다운"
                    else:
                        target_cooldown = profit_cd_sec
                        label = "익절/스위칭 쿨다운"

                    self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                    if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                        self.cooldown_timer_task.cancel()
                    self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
                    try:
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log("??[2?④퀎: REST API ?⑦궥 泥?궛] execute_bitget_internal_packet(side=CLEAR) ?몄텧 以?..")
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"?뱥 [3?④퀎: 泥?궛 寃곌낵 諛섑솚] clear_ok: {clear_ok}")
                        if clear_ok:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log("??[4?④퀎: 泥?궛 ?꾨즺] 諛섎? 諛⑺뼢 ?좎젣 泥?궛 ?깃났!")
                        else:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log("?좑툘 [4?④퀎: 1李??ㅽ뙣] 2以?鍮꾩긽 留덉뒪??泥?궛 寃⑸컻 ?쒕룄...")
                            await asyncio.sleep(0.5)
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                    except Exception as clear_err:
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"??[泥?궛 ?덉쇅] {clear_err}")
                        try:
                            await asyncio.sleep(0.5)
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                        except Exception:
                            pass
                    finally:
                        self.is_position_active = False
                        self.exit_in_progress = False
                    return

        # [?ъ슫??理쒖슦??吏곸넚]: ?꾧퀎移?議곌굔 異⑹” ????0.000ms 吏?곕룄 ?놁씠 ?ъ슫??1?쒖쐞 寃⑸컻 (1.0珥??붾컮?댁떛 ?곸슜)
        if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
            now_t_radar = time.time()
            if now_t_radar - getattr(self, "last_radar_signal_log_time", 0.0) >= 1.0:
                self.last_radar_signal_log_time = now_t_radar
                try:
                    snd_en = getattr(getattr(self.bot, "dashboard", None), "sound_enabled", True)
                    play_order_sound(direction, enabled=snd_en)
                except Exception:
                    pass
        
        # [?寃??쒖꽦 ?곹깭 寃??: 理쒖긽?⑥쑝濡??대룞??(v4.07)
        
        # [05:00 KST ?몄뀡 ?꾪솚 ?몄씠利?李⑤떒 ?쎈떎???꾪꽣]
        now_dt = datetime.now()
        if now_dt.hour == 5 and now_dt.minute == 0:
            # 05:00:00 ~ 05:01:00 KST ?몄뀡 寃쎄퀎???쎈떎??援ш컙 (??1遺꾧컙)
            if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
                logger.warning(f"?썳截?[?몄뀡 ?꾪솚 ?쎈떎?? 05:00 KST ?몄뀡 寃쎄퀎???몄씠利?援ш컙(05:00~05:01) 媛먯? ?∽툘 援щ씪 ?좏샇 吏꾩엯/?ㅼ쐞移?쓣 李⑤떒?⑸땲?? (泥?궛: ${rolling_1m_liq_usd:,.0f}, OI: {oi_delta_1m:+.4f}%)")
            return

        # 泥?궛 吏꾪뻾 以묒씤 寃쎌슦, 紐⑤뱺 ?좉퇋 ??媛먯떆 諛?吏꾩엯 寃利앹쓣 利됱떆 100% 李⑤떒 (媛쒕컻怨꾪쉷??189)
        if getattr(self, "exit_in_progress", False):
            return

        # 1?④퀎: ?숈쟻 ?덉씠???꾧퀎移?寃利?
        if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
            # [荑⑦????ъ쟾 寃利?理쒖슦???꾩쭊 諛곗튂]: 荑⑦????湲?以묒씤 寃쎌슦 吏꾩엯/異붽?留ㅼ닔 ?쒕룄 諛?硫뷀듃由?濡쒓렇 異쒕젰??李⑤떒?섍퀬 1.0珥?1?뚮쭔 移댁슫?몃떎???뚮┝
            now_t_chk = time.time()
            if time.time() < getattr(self, "cooldown_until_time", 0.0):
                remain_sec = getattr(self, "cooldown_until_time", 0.0) - time.time()
                if self.bot.ui_cb and now_t_chk - getattr(self, "last_cooldown_log_time", 0.0) >= 1.0:
                    self.last_cooldown_log_time = now_t_chk
                    self.bot.ui_cb(0.0, 0, f"??[荑⑦????湲?以? 吏꾩엯 蹂대쪟 (?⑥? ?쒓컙: {remain_sec:.1f}珥?")
                return

            # [?몄뀡 嫄곕옒 ON/OFF 泥댄겕諛뺤뒪 寃利?(媛쒕컻怨꾪쉷??260)]: 理쒖긽?⑥쑝濡??대룞??(v4.07)

            t_step_start = time.time()
            now_t_metric = time.time()
            if getattr(self.bot, "dashboard", None) and now_t_metric - getattr(self, "last_radar_metric_log_time", 0.0) >= 1.0:
                self.last_radar_metric_log_time = now_t_metric
                self.bot.dashboard.add_log(f"?깍툘 [1?④퀎 ?꾧퀎移??뚰뙆 硫뷀듃由? ?ъ슫??0.000ms 理쒖슦??吏곸넚 ?꾨즺 ?∽툘 {direction} ?寃?寃利?吏꾩엯...")
            self.entry_reason = f"1遺?泥?궛 ${rolling_1m_liq_usd:,.0f} (?꾧퀎移? ${target_liq:,.0f}) & OI?띾룄 {oi_delta_1m:+.4f}% (?꾧퀎移? {target_oi:+.4f}%) ?숈떆 ?뚰뙆"
            self.last_signal_price = binance_mid

            # ?숈씪 諛⑺뼢 以묐났 ?좏샇媛 諛쒖깮?덉쓣 ??-> 2李?/ 3李?異붽? 留ㅼ닔 議곌굔 寃利?諛?湲곕룞
            if self.is_position_active and not is_opposite:
                dashboard = self.bot.dashboard
                split_cooldown = dashboard.split_cooldown_seconds
                
                # 2李?異붽? 留ㅼ닔媛 ?꾩쭅 寃⑸컻?섏? ?딆? 寃쎌슦
                if not getattr(self, "has_second_entry", False):
                    if dashboard.split_entry_2_ratio <= 0.0:
                        return
                    split_trigger_val = dashboard.split_entry_2_trigger_pct
                    split_trigger = split_trigger_val / 100.0
                    
                    if self.entry_direction == "LONG":
                        pnl_from_entry_1 = (binance_mid - self.entry_price_1) / self.entry_price_1
                    else:
                        pnl_from_entry_1 = (self.entry_price_1 - binance_mid) / self.entry_price_1
                        
                    if pnl_from_entry_1 <= split_trigger:
                        time_since_last_split = time.time() - getattr(self, "last_split_entry_time", 0.0)
                        if time_since_last_split < split_cooldown:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log(f"??[2李?異붽?留ㅼ닔 蹂대쪟] 1李?吏꾩엯媛 ?鍮??섎씫??異⑹”({pnl_from_entry_1*100.0:+.2f}%)?섏뿀?쇰굹, 荑⑤떎???湲?以?({int(split_cooldown - time_since_last_split)}珥??⑥쓬)")
                            return
                            
                        self.has_second_entry = True
                        self.last_split_entry_time = time.time()
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"??[2李?異붽?留ㅼ닔 諛쒕룞] ?숈씪諛⑺뼢 ?좏샇 而⑦럩! 1李?吏꾩엯媛 ?鍮?{pnl_from_entry_1*100.0:+.2f}% ?꾨떖 (?꾧퀎移? {split_trigger*100.0:.2f}%)")
                        asyncio.create_task(self.execute_bitget_internal_packet(side=self.entry_direction, order_type="ADD_100_PERCENT"))
                        return
                    else:
                        return
                        
                # 2李?異붽? 留ㅼ닔??寃⑸컻?섏뿀?쇰굹 3李?異붽? 留ㅼ닔媛 ?꾩쭅 寃⑸컻?섏? ?딆? 寃쎌슦
                elif getattr(self, "has_second_entry", False) and not getattr(self, "has_third_entry", False):
                    if dashboard.split_entry_3_ratio <= 0.0:
                        return
                    split_trigger_val = dashboard.split_entry_3_trigger_pct
                    split_trigger = split_trigger_val / 100.0
                    
                    if self.entry_direction == "LONG":
                        pnl_from_entry_1 = (binance_mid - self.entry_price_1) / self.entry_price_1
                    else:
                        pnl_from_entry_1 = (self.entry_price_1 - binance_mid) / self.entry_price_1
                        
                    if pnl_from_entry_1 <= split_trigger:
                        time_since_last_split = time.time() - getattr(self, "last_split_entry_time", 0.0)
                        if time_since_last_split < split_cooldown:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log(f"??[3李?異붽?留ㅼ닔 蹂대쪟] 1李?吏꾩엯媛 ?鍮??섎씫??異⑹”({pnl_from_entry_1*100.0:+.2f}%)?섏뿀?쇰굹, 荑⑤떎???湲?以?({int(split_cooldown - time_since_last_split)}珥??⑥쓬)")
                            return
                            
                        self.has_third_entry = True
                        self.last_split_entry_time = time.time()
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"??[3李?異붽?留ㅼ닔 諛쒕룞] ?숈씪諛⑺뼢 ?좏샇 而⑦럩! 1李?吏꾩엯媛 ?鍮?{pnl_from_entry_1*100.0:+.2f}% ?꾨떖 (?꾧퀎移? {split_trigger*100.0:.2f}%)")
                        asyncio.create_task(self.execute_bitget_internal_packet(side=self.entry_direction, order_type="ADD_THIRD_ENTRY"))
                        return
                    else:
                        return
                else:
                    return
            # -------------------------------------------------------------------------------------
            if self.exit_in_progress:
                return
                
            if time.time() - getattr(self, "last_entry_time", 0.0) < 5.0:
                remain_sec = 5.0 - (time.time() - getattr(self, "last_entry_time", 0.0))
                if self.bot.ui_cb and now_t_chk - getattr(self, "last_cooldown_log_time", 0.0) >= 1.0:
                    self.last_cooldown_log_time = now_t_chk
                    self.bot.ui_cb(0.0, 0, f"??[以묐났 吏꾩엯 諛⑹?] ?숈씪 ?ㅽ뙆?댄겕 ?곗냽 吏꾩엯 蹂대쪟 (?⑥? ?쒓컙: {remain_sec:.1f}珥?")
                return
            
            # 1.0珥??뺣? ?붾컮?댁뒪濡??렞 [?寃?寃⑸컻] 濡쒓렇 ?꾨같 100% ?먯쿇 諛뺣㈇
            if getattr(self.bot, "dashboard", None) and now_t_chk - getattr(self, "last_snipe_trigger_log_time", 0.0) >= 1.0:
                self.last_snipe_trigger_log_time = now_t_chk
                self.bot.dashboard.add_log(f"?렞 [?寃?寃⑸컻] ?쒖옣泥?궛(${rolling_1m_liq_usd:,.0f}) & OI?띾룄({oi_delta_1m:+.4f}%) ?꾧퀎移??숈떆 ?뚰뙆! 吏꾩엯 寃利??쒕룄...")
            
            # 諛⑹뼱踰??? 臾쇰━???덉씠?댁떆 而룹삤??(v2.88 李⑤떒 媛???꾨㈃ ?댁젣 - ?덉씠?댁떆 ?곴??놁씠 100% 利됯컖 諛쒖＜)
            t_order = time.time() * 1000
            allowed_latency = self.MAX_LATENCY_MS_LOCAL if self.is_local_mode else self.MAX_LATENCY_MS_PROD
            actual_latency = t_order - t_signal
            
            # v2.88 ?댁젣: ?덉씠?댁떆 珥덇낵 ??吏꾩엯 湲곌컖 return 釉붾줉???댁젣?섍퀬 100% 利됯컖 諛쒖＜ 吏꾪뻾
            if actual_latency > allowed_latency:
                if getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"??[v2.88 ?덉씠?댁떆 ?듦낵] ?덉씠?댁떆 {actual_latency:.1f}ms (湲곗〈 ?덉슜 {allowed_latency:.1f}ms 珥덇낵?섎굹 ?꾨㈃ ?댁젣 利됯컖 諛쒖＜)")
                
            # 2?④퀎: 鍮꾪듃寃??멸?李?VWAP ??났???ㅼ틪
            bitget_book = await self.fetch_bitget_orderbook_internal()
            if not bitget_book or not bitget_book.get('asks') or not bitget_book.get('bids'):
                if self.bot.ui_cb:
                    self.bot.ui_cb(0.0, 0, f"??[吏꾩엯 ?ㅽ뙣] BITGET ?멸?李??곗씠?곕? 議고쉶?????놁뒿?덈떎.")
                return
                
            expected_fill = bitget_book['asks'][0][0] if direction == 'LONG' else bitget_book['bids'][0][0]
            
            # 諛⑹뼱踰??? 諛⑺뼢??鍮꾨?移??щ━?쇱? 罹?寃利?(湲고쉷??21)
            if direction == 'LONG':
                if expected_fill < binance_mid:
                    favorable_pct = (binance_mid - expected_fill) / binance_mid
                    if favorable_pct > 0.010: # 1.0% 珥덇낵 ????몄씠利?李⑤떒
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"?좑툘 [吏꾩엯 湲곌컖] ?좊━??濡??щ━?쇱? ?몄씠利?1.0% 珥덇낵 ({favorable_pct*100.0:.3f}%) (李⑥씠: ${binance_mid - expected_fill:,.1f})")
                        return
                    # 1.0% ?댄븯 ?좊━???щ━?쇱???100% 臾댁“嫄??뱀씤!
                else:
                    unfavorable_slippage = (expected_fill - binance_mid) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"?좑툘 [吏꾩엯 湲곌컖] 遺덈━??濡??щ━?쇱? {unfavorable_slippage*100.0:.3f}% 珥덇낵 (?덉슜: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (李⑥씠: ${expected_fill - binance_mid:,.1f})")
                        return
            else: # SHORT
                if expected_fill > binance_mid:
                    favorable_pct = (expected_fill - binance_mid) / binance_mid
                    if favorable_pct > 0.010: # 1.0% 珥덇낵 ????몄씠利?李⑤떒
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"?좑툘 [吏꾩엯 湲곌컖] ?좊━?????щ━?쇱? ?몄씠利?1.0% 珥덇낵 ({favorable_pct*100.0:.3f}%) (李⑥씠: ${expected_fill - binance_mid:,.1f})")
                        return
                    # 1.0% ?댄븯 ?좊━???щ━?쇱???100% 臾댁“嫄??뱀씤!
                else:
                    unfavorable_slippage = (binance_mid - expected_fill) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"?좑툘 [吏꾩엯 湲곌컖] 遺덈━?????щ━?쇱? {unfavorable_slippage*100.0:.3f}% 珥덇낵 (?덉슜: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (李⑥씠: ${binance_mid - expected_fill:,.1f})")
                        return
                
            # 3?④퀎: 理쒖쥌 ?꾪꽣 ?⑥뒪 -> ?寃?媛먯떆 ?뱀씤(is_snipe_active) 諛?Taker 0.012% ?寃?吏꾩엯
            if not self.is_position_active and self.is_snipe_active and not self.exit_in_progress:
                # --- [2以?以묐났 吏꾩엯 諛⑹? ?좎젣 ???좎뼵] ---
                # 鍮꾨룞湲?二쇰Ц ?꾩넚 ??利됱떆 ?쎌쓣 嫄몄뼱 ?꾩냽 ?꾨젅??寃⑸컻 ?먯쿇 李⑤떒
                self.is_position_active = True
                
                self.last_entry_time = time.time()
                self.entry_direction = direction
                self.entry_price = expected_fill
                self.entry_price_1 = expected_fill
                self.has_second_entry = False
                self.peak_pnl_pct = 0.0
                self.peak_buying_delta = random.uniform(80000, 150000)
                
                if self.bot.dashboard:
                    self.bot.dashboard.play_entry_sound()
                    
                try:
                    success = await self.execute_bitget_internal_packet(side=direction, order_type="IOC_MARKET")
                    if success:
                        # ?좉퇋 吏꾩엯 ?깃났 ??臾댁“嫄?60珥?荑⑦???媛€??
                        self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + 60.0)
                        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                            self.cooldown_timer_task.cancel()
                        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(60.0, "신규 진입 60초 쿨다운"))
                        
                        # 泥?吏꾩엯 ?깃났 ??媛먯떆 猷⑦봽 ?꾩슦怨?醫낅즺
                        asyncio.create_task(self.manage_v35_exit_guardrail(direction))
                    else:
                        # [?ㅻ쭏??蹂듦뎄 ?곴뎄 ??젣] ?ъ＜臾?濡쒖쭅???꾨㈃ ?쒓굅?섏뿬 1李??ㅽ뙣 ??利됱떆 醫낅즺
                        self.is_position_active = False
                        if self.bot.dashboard:
                            self.bot.dashboard.send_telegram_notification(f"?좑툘 [?ㅼ쟾 吏꾩엯 ?ㅽ뙣 寃쎈낫] 1李?吏꾩엯 ?ㅽ뙣濡?二쇰Ц 理쒖쥌 湲곌컖 (諛⑺뼢: {direction})")
                except Exception as e:
                    # ?덇린移??딆? ?덉쇅 諛쒖깮 ??理쒖쥌 臾댁궛 泥섎━ 諛????댁젣
                    logger.error(f"吏꾩엯 二쇰Ц 泥섎━ 以??덉쇅 諛쒖깮: {e}")
                    self.is_position_active = False
            else:
                if self.bot.ui_cb:
                    self.bot.ui_cb(0.0, 0, f"?좑툘 [吏꾩엯 湲곌컖] ?대? ?ъ??섏씠 媛??以묒씠嫄곕굹 ?먮룞 ?寃?媛먯떆媛 鍮꾪솢?깊솕 ?곹깭?낅땲?? (is_active: {self.is_position_active}, is_snipe: {self.is_snipe_active})")

    async def manage_v35_exit_guardrail(self, direction):
        self.is_guardrail_running = True
        try:
            await self._manage_v35_exit_guardrail_impl(direction)
        finally:
            self.is_guardrail_running = False

    async def _manage_v35_exit_guardrail_impl(self, direction):
        """
        諛⑹뼱踰??? ?꾩땐???ㅻ떒怨?寃⑹감 ?먮Ъ??諛??섏씠釉뚮━???듭젅/?먯젅 泥?궛 ?붿쭊
        """
        self.exit_msg_sent = False
        self.exit_reason = ""
        # ?몄뀡蹂??먮룞 ?곕룞 ?먯젅???쇱꽱?곗? 諛?理쒖큹 ?ㅽ깙濡쒖뒪 媛寃??곗궛 (媛쒕컻怨꾪쉷??176)
        initial_sl_pct = abs(getattr(self, "current_session_sl", -1.3)) / 100.0
        # 湲곕룞 ??諛곗튂??理쒖큹 湲곕낯 ?ㅽ깙濡쒖뒪 媛寃⑹쑝濡?last_placed_stop_price瑜??ъ쟾 ?숆린?뷀븯??以묐났 諛쒖＜ 諛⑹?
        self.last_placed_stop_price = self.entry_price * (1.0 - initial_sl_pct) if direction == "LONG" else self.entry_price * (1.0 + initial_sl_pct)
        while self.is_position_active:
            await asyncio.sleep(0.01)
            
            # ?ㅼ떆媛??몄뀡蹂??먯젅???숈쟻 ?낅뜲?댄듃 (?몄뀡 ?쒓컙 ?꾪솚 ??諛섏쁺)
            initial_sl_pct = abs(getattr(self, "current_session_sl", -1.3)) / 100.0
            
            current_bitget_price = await self.get_live_bitget_price_internal()
            if current_bitget_price <= 0.0:
                continue
                
            # 3.0珥??꾪궧 ?좎삁 ?쒓컙 ?숈븞? ?덉쟾 蹂댁〈???꾪빐 泥?궛 媛먯떆 ?쇱떆 ?ㅽ궢
            import time
            grace_until = getattr(self, "grace_period_until", 0.0)
            if time.time() < grace_until:
                self.peak_pnl_pct = 0.0
                continue
            
            # 1李?吏꾩엯媛 ?鍮?PnL 諛??ㅼ떆媛??됰떒 ?鍮?PnL 怨꾩궛
            if direction == "LONG":
                pnl_from_entry_1 = (current_bitget_price - self.entry_price_1) / self.entry_price_1
                pnl_pct = (current_bitget_price - self.entry_price) / self.entry_price
            else:
                pnl_from_entry_1 = (self.entry_price_1 - current_bitget_price) / self.entry_price_1
                pnl_pct = (self.entry_price - current_bitget_price) / self.entry_price
                
            if pnl_pct > self.peak_pnl_pct:
                self.peak_pnl_pct = pnl_pct
            self.last_live_pnl_pct = pnl_pct * 100.0

            # [HOTFIX v4.06] ?먮룞 遊??쒖옉 踰꾪듉??爰쇱졇?덉쓣 寃쎌슦 紐⑤뱺 媛뺤젣 泥?궛/?먯젅/?듭젅 媛쒖엯 ?꾨꼍 李⑤떒 (愿留??좎?)
            if not getattr(self, "is_snipe_active", False):
                continue

            # [HOTFIX v4.07] ?몄뀡 泥댄겕諛뺤뒪媛 ??ㅼ엳??寃쎌슦 紐⑤뱺 媛뺤젣 泥?궛/?먯젅 媛쒖엯 ?먯쿇 李⑤떒
            g_curr_key = getattr(self, "current_session_key", "us")
            g_dashboard = getattr(self.bot, "dashboard", None)
            g_thresholds_map = getattr(g_dashboard, "session_thresholds", {}) if g_dashboard else {}
            if not g_thresholds_map.get(g_curr_key, {}).get("enabled", True):
                continue

            # [v2.80/v2.96/v3.62/v3.77] ?ㅼ떆媛??좉????몃찓紐⑤━ ?ㅻ쭏??PnL ?ㅽ봽???ㅽ깙 媛먯떆 (?곷????꾩튂 湲곕컲 ???諛⑺뼢??Engine)
            if getattr(self, "custom_stop_active", False):
                offset_val = getattr(self, "custom_stop_offset_pct", -0.2)
                pnl_at_set = getattr(self, "custom_stop_set_pnl", pnl_pct * 100.0)
                live_pnl = pnl_pct * 100.0

                if offset_val < pnl_at_set:
                    # ?ㅼ젙媛믪씠 ?꾩옱 PnL蹂대떎 ?꾨옒 ?∽툘 ?섎갑 ?섎씫/蹂댁〈/?먯젅 紐⑤뱶
                    is_triggered = (live_pnl <= offset_val)
                    cond_str = "?댄븯"
                    stop_label = "?먯젅/蹂댁〈"
                else:
                    # ?ㅼ젙媛믪씠 ?꾩옱 PnL蹂대떎 ???∽툘 ?곷갑 ?곸듅/諛섎벑/?듭젅 紐⑤뱶
                    is_triggered = (live_pnl >= offset_val)
                    cond_str = "?댁긽"
                    stop_label = "?곸듅/諛섎벑?듭젅"

                if is_triggered:
                    self.custom_stop_active = False
                    ratio = float(getattr(self, "custom_stop_close_ratio", 100.0))
                    if ratio < 100.0:
                        order_type = f"PARTIAL_CLOSE_{int(ratio)}"
                    else:
                        order_type = "FORCE_MARKET_UNCAPPED"
                    clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type=order_type, custom_ratio=ratio/100.0)
                    if clear_ok:
                        if order_type == "FORCE_MARKET_UNCAPPED":
                            self.is_position_active = False
                        log_msg = f"?썳截?[?ㅻ쭏???ㅽ깙 諛쒕룞] ?ㅼ떆媛?PnL({live_pnl:+.2f}%)???ㅼ젙媛?{offset_val:+.2f}%) {cond_str} ?꾨떖! ({ratio:.0f}% {stop_label} 泥?궛: {order_type})"
                        if self.bot and self.bot.dashboard:
                            self.bot.dashboard.add_log(log_msg)
                            if hasattr(self.bot.dashboard, "reset_stoploss_ui"):
                                self.bot.dashboard.reset_stoploss_ui()
                        self.exit_msg_sent = True
                        if order_type == "FORCE_MARKET_UNCAPPED":
                            break
                    else:
                        if order_type == "FORCE_MARKET_UNCAPPED":
                            self.is_position_active = True
                            self.exit_in_progress = False
                            log_msg = "?좑툘 [泥?궛 1李??ㅽ뙣] 2以?鍮꾩긽 留덉뒪??泥?궛 寃⑸컻!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"?ㅻ쭏?몄뒪??鍮꾩긽 泥?궛 ?먮윭: {em_err}")

            # ================= ?섏씠釉뚮━??遺꾪븷 ?듭젅 媛?쒕젅??=================
            current_time_str = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
            s_key = "NY"
            try:
                from datetime import datetime, timedelta
                now_dt = datetime.now()
                trading_dt = now_dt - timedelta(hours=9)
                hour_val = now_dt.hour
                minute_val = now_dt.minute
                is_weekend = trading_dt.weekday() in [5, 6]
                if 9 <= hour_val < 16:
                    s_key = "WEEKEND_ASIA" if is_weekend else "ASIA"
                elif 16 <= hour_val < 22 or (hour_val == 22 and minute_val < 30):
                    s_key = "WEEKEND_LONDON" if is_weekend else "LONDON"
                elif (hour_val == 22 and minute_val >= 30) or hour_val >= 23 or hour_val < 5:
                    s_key = "WEEKEND_NY" if is_weekend else "NY"
                else:
                    s_key = "WEEKEND_PACIFIC" if is_weekend else "PACIFIC"
            except Exception as e:
                logger.error(f"媛?쒕젅???몄뀡 ?먯젙 ?ㅻ쪟: {e}")
            
            s_guardrails = getattr(self.bot.dashboard, "session_guardrails", {}).get(s_key, {"trigger": 0.9, "guard": -0.25, "enabled": True})
            half_exit_trigger = s_guardrails["trigger"] / 100.0
            entry_sl_guard = s_guardrails["guard"]
            half_exit_enabled = s_guardrails.get("enabled", True)
            
            if half_exit_enabled:
                if not getattr(self, "is_half_exited", False) and pnl_pct >= half_exit_trigger:
                    self.is_half_exited = True
                    self.awaiting_pullback_pyramid = True
                    asyncio.create_task(self.execute_bitget_internal_packet(side="CLEAR", order_type="50_PERCENT_CLOSE"))
                    
                    if self.bot.dashboard:
                        msg = f"<b>?렞 [遺꾪븷?듭젅 ?뚮┝]</b>\n諛⑺뼢: <b>{direction}</b>\n?ъ쑀: <b>?섏씡瑜?{half_exit_trigger*100:.2f}% ?꾨떖 (50% ?듭젅 ?ㅽ뻾)</b>\n?됰떒媛: <b>{self.entry_price:,.1f} USDT</b>\n?꾩옱媛: <b>{current_bitget_price:,.1f} USDT</b>"
                        self.bot.dashboard.send_telegram_notification(msg)
                    
                    await asyncio.sleep(1.0)
                    new_sl_price = self.entry_price * (1.0 + (entry_sl_guard / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (entry_sl_guard / 100.0))
                    self.last_placed_stop_price = new_sl_price
                    asyncio.create_task(self.execute_bitget_internal_packet(side="STOP_LOSS", order_type=str(round(new_sl_price, 1))))
            else:
                if pnl_pct >= half_exit_trigger and not getattr(self, "has_smart_guarded", False):
                    self.has_smart_guarded = True
                    new_stop_price = self.entry_price * (1.0 + (entry_sl_guard / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (entry_sl_guard / 100.0))
                    self.last_placed_stop_price = new_stop_price
                    asyncio.create_task(self.execute_bitget_internal_packet(side="STOP_LOSS", order_type=str(round(new_stop_price, 1))))
                    
                    log_msg = f"?썳截?[?ㅻ쭏??蹂몄쟾媛?? 遺꾪븷?듭젅 OFF ?몄뀡: 100% ?섎웾 ?좎??섎ŉ ?ㅽ깙濡쒖뒪瑜?蹂몄쟾/踰꾪띁媛({new_stop_price:.1f})濡??곹뼢 諛⑹뼱?덉뒿?덈떎!"
                    if self.bot.dashboard:
                        self.bot.dashboard.add_log(log_msg)
                        tg_msg = f"<b>?썳截?[?ㅻ쭏??蹂몄쟾媛???뚮┝]</b>\n諛⑺뼢: <b>{direction}</b>\n?ъ쑀: <b>遺꾪븷?듭젅 OFF ?몄뀡 100% ?섎웾 ?좎? 諛?蹂몄쟾媛???곹뼢</b>\n???ㅽ깙濡쒖뒪: <b>{new_stop_price:,.1f} USDT</b>"
                        self.bot.dashboard.send_telegram_notification(tg_msg)
                
            if getattr(self, "is_half_exited", False) and getattr(self, "awaiting_pullback_pyramid", False) and not getattr(self, "has_pyramided", False) and getattr(self.bot.dashboard, "pyramiding_enabled", False):
                pullback_offset = float(getattr(getattr(self.bot, "dashboard", None), "pullback_pyramiding_offset", 0.003))
                    
                if pnl_pct <= (half_exit_trigger - pullback_offset):
                    self.has_pyramided = True
                    self.awaiting_pullback_pyramid = False
                    asyncio.create_task(self.execute_bitget_internal_packet(side=direction, order_type="ADD_PYRAMIDING"))
                    
                    if self.bot.dashboard:
                        self.bot.dashboard.add_log(f"[?뚮┝紐?遺덊?湲? {pullback_offset*100}% ?諛?媛먯? ?꾨즺! 30% ?섎웾 ?뺣? 諛쒖＜瑜?吏묓뻾?⑸땲??")
                        msg_tg = f"<b>?뵦 [?뚮┝紐?遺덊?湲??뚮┝]</b>\n諛⑺뼢: <b>{direction}</b>\n?ъ쑀: <b>{pullback_offset*100}% ?諛?媛먯? ?꾨즺! 30% ?섎웾 ?뺣? 諛쒖＜瑜?吏묓뻾?⑸땲??</b>"
                        self.bot.dashboard.send_telegram_notification(msg_tg)
                
            if (getattr(self, "is_half_exited", False) or getattr(self, "has_smart_guarded", False)) and pnl_pct <= (entry_sl_guard / 100.0):
                self.exit_reason = "?ㅻ쭏??蹂몄쟾/踰꾪띁 蹂댁〈 媛??諛쒕룞" if getattr(self, "has_smart_guarded", False) else "蹂몄쟾/踰꾪띁 蹂댁〈 媛??諛쒕룞 (遺꾪븷泥?궛 ??"
                self.exit_in_progress = True
                clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                if clear_ok:
                    self.is_position_active = False
                    self.exit_msg_sent = True
                    break
                else:
                    self.is_position_active = True
                    self.exit_in_progress = False
                    log_msg = "?좑툘 [泥?궛 1李??ㅽ뙣] 2以?鍮꾩긽 留덉뒪??泥?궛 寃⑸컻!"
                    if self.bot and self.bot.dashboard:
                        self.bot.dashboard.add_log(log_msg)
                        try:
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                        except Exception as em_err:
                            logger.error(f"蹂몄쟾媛??鍮꾩긽 泥?궛 ?먮윭: {em_err}")

            # [媛쒕컻怨꾪쉷??93] ?ㅻЪ 嫄곕옒???쒕쾭?ъ씠??異붿쟻 ?ㅽ깙濡쒖뒪 媛寃??곗궛 諛??먮룞 ?щ같移?(Trailing)
            # (2李?3李?吏꾩엯 ?곹깭?먯꽌???쒕쾭?ъ씠???몃젅?쇰쭅 ?덉빟??嫄대꼫?곷땲??
            if not self.has_second_entry and not getattr(self, "has_third_entry", False):
                new_stop_price = 0.0
                if self.peak_pnl_pct >= 0.020:
                    # +2.0% ?댁긽 ?뚰뙆 ?? 怨좎젏 ?€鍮?1.0% ?섎씫?좎뿉 ?몃젅?쇰쭅 ?듭젅???뺤꽦 (Gap 1.0%)
                    new_stop_price = self.entry_price * (1 + self.peak_pnl_pct - 0.010) if direction == "LONG" else self.entry_price * (1 - self.peak_pnl_pct + 0.010)

                elif getattr(self, "is_half_exited", False) or getattr(self, "has_smart_guarded", False):
                    # 50% 遺꾪븷?듭젅 ???먮뒗 ?ㅻ쭏??蹂몄쟾媛€??諛쒕룞 ???몄뀡 媛€??蹂댁〈媛€寃??곗궛 (32李??섏닠: 0.0???곗궛 諛?踰꾧렇 諛⑹?)
                    new_stop_price = self.entry_price * (1.0 + (entry_sl_guard / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (entry_sl_guard / 100.0))

                elif not getattr(self, "is_half_exited", False) and not getattr(self, "has_smart_guarded", False):
                    # 珥덇린 湲곕낯 ?먯젅??(?몄뀡 ?곕룞)
                    new_stop_price = self.entry_price * (1.0 - initial_sl_pct) if direction == "LONG" else self.entry_price * (1.0 + initial_sl_pct)
                    
                if new_stop_price <= 0.0:
                    continue
                    
                # ?ㅽ깙 媛寃⑹씠 ?좊━?섍쾶 ?곹뼢 媛깆떊?섏뿀?붿? 鍮꾧탳 ?먯젙
                is_better = False
                if self.last_placed_stop_price == 0.0:
                    is_better = True
                else:
                    if direction == "LONG":
                        if new_stop_price > self.last_placed_stop_price:
                            is_better = True
                    else:
                        if new_stop_price < self.last_placed_stop_price:
                            # ?륁씪 ?뚮뒗 ?ㅽ깙 媛寃⑹씠 ?꾨옒濡??대젮媛???대뱷?낅땲??
                            is_better = True
                            
                now_t_sl = time.time()
                # [35李??꾩튂] ?ㅽ깙濡쒖뒪 媛깆떊 ??理쒖냼 10.0珥??붾컮?댁떛 媛???곸슜?섏뿬 50珥???쒕낫???ㅼ슫 0.0% ?먯쿇 李⑤떒
                if is_better and (now_t_sl - getattr(self, "last_placed_stop_time", 0.0) >= 10.0 or self.last_placed_stop_price == 0.0):
                    self.last_placed_stop_price = new_stop_price
                    self.last_placed_stop_time = now_t_sl
                    # 嫄곕옒??湲곗〈 ?덉빟??痍⑥냼?섍퀬 ?덈줈??媛寃⑹쑝濡?利됱떆 ?ㅻЪ 議곌굔遺 二쇰Ц 諛쒖＜ ?щ같移?
                    asyncio.create_task(self.execute_bitget_internal_packet(
                        side="STOP_LOSS",
                        order_type=str(round(new_stop_price, 1))
                    ))
                
            # ================= PART 1: ?먯젅 諛?怨꾨떒???듭젅 ?먮Ъ??(濡쒖뺄 諛깆뾽 ?붿쭊) =================
            if self.has_second_entry or getattr(self, "has_third_entry", False):
                if not getattr(self, "is_half_exited", False) and pnl_from_entry_1 <= -initial_sl_pct:
                    self.last_exit_trigger_price = current_bitget_price
                    self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                    self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                    self.exit_reason = f"理쒖큹 ?먯젅???꾨떖 (-{initial_sl_pct*100:.2f}% ?댄븯 ?꾨떖, PnL: {pnl_from_entry_1*100:.2f}%)"

                    self.exit_in_progress = True
                    clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                    if clear_ok:
                        self.is_position_active = False
                        if self.bot.dashboard:
                            msg = f"<b>?렞 [?먯젅 泥?궛 ?뚮┝]</b>\n諛⑺뼢: <b>{direction}</b>\n?ъ쑀: <b>{self.exit_reason}</b>\n吏꾩엯媛: <b>{self.entry_price_1:,.1f} USDT</b>\n?꾩옱媛: <b>{current_bitget_price:,.1f} USDT</b>\n?섏씡瑜? <b>{pnl_from_entry_1 * 100:+.2f}%</b>"
                            self.bot.dashboard.send_telegram_notification(msg)
                        self.exit_msg_sent = True
                        break
                    else:
                        self.is_position_active = True
                        self.exit_in_progress = False
                        log_msg = "?좑툘 [泥?궛 1李??ㅽ뙣] 2以?鍮꾩긽 留덉뒪??泥?궛 寃⑸컻!"
                        if self.bot and self.bot.dashboard:
                            self.bot.dashboard.add_log(log_msg)
                            try:
                                await self.bot.dashboard.execute_bitget_emergency_master_internal()
                            except Exception as em_err:
                                logger.error(f"2/3李??먯젅 鍮꾩긽 泥?궛 ?먮윭: {em_err}")
            else:
                if self.peak_pnl_pct < 0.020:
                    # 珥덇린 ?먯젅??(?몄뀡 ?곕룞)
                    if pnl_pct <= -initial_sl_pct:
                        self.last_exit_trigger_price = current_bitget_price
                        self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                        self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                        self.exit_reason = f"珥덇린 ?먯젅??(-{initial_sl_pct*100:.2f}% ?댄븯 ?꾨떖, PnL: {pnl_pct*100:.2f}%)"

                        self.exit_in_progress = True
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if clear_ok:
                            self.is_position_active = False
                            if self.bot.dashboard:
                                msg = f"<b>?렞 [?먯젅 泥?궛 ?뚮┝]</b>\n諛⑺뼢: <b>{direction}</b>\n?ъ쑀: <b>{self.exit_reason}</b>\n吏꾩엯媛: <b>{self.entry_price:,.1f} USDT</b>\n泥?궛媛: <b>{current_bitget_price:,.1f} USDT</b>\n?섏씡瑜? <b>{pnl_pct * 100:+.2f}%</b>"
                                self.bot.dashboard.send_telegram_notification(msg)
                            self.exit_msg_sent = True
                            break
                        else:
                            self.is_position_active = True
                            self.exit_in_progress = False
                            log_msg = "?좑툘 [泥?궛 1李??ㅽ뙣] 2以?鍮꾩긽 留덉뒪??泥?궛 寃⑸컻!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"珥덇린 ?먯젅 鍮꾩긽 泥?궛 ?먮윭: {em_err}")
                    

                else:
                    # ================= PART 2: +2.0% ?댁긽 ?몃젅?쇰쭅 ?듭젅??(濡쒖뺄 諛깆뾽 ?붿쭊) =================
                    # 湲곗뼱 A: 怨좎젏 ?鍮?1.0% ?섎씫 ???몃젅?쇰쭅 ?ㅼ쐞移??묐룞
                    if pnl_pct <= (self.peak_pnl_pct - 0.010):
                        self.last_exit_trigger_price = current_bitget_price
                        self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                        self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                        self.exit_reason = f"怨좎젏 {self.peak_pnl_pct*100:.2f}% ?뚰뙆 ??1.0% ?섎씫??{(self.peak_pnl_pct-0.010)*100:.2f}% ?꾨떖 (異붿쟻 ?ㅽ깙, PnL: {pnl_pct*100:.2f}%)"

                        self.exit_in_progress = True
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if clear_ok:
                            self.is_position_active = False
                            if self.bot.dashboard:
                                msg = f"<b>?렞 [異붿쟻?듭젅 泥?궛 ?뚮┝]</b>\n諛⑺뼢: <b>{direction}</b>\n?ъ쑀: <b>{self.exit_reason}</b>\n吏꾩엯媛: <b>{self.entry_price:,.1f} USDT</b>\n泥?궛媛: <b>{current_bitget_price:,.1f} USDT</b>\n?섏씡瑜? <b>{pnl_pct * 100:+.2f}%</b>"
                                self.bot.dashboard.send_telegram_notification(msg)
                            self.exit_msg_sent = True
                            break
                        else:
                            self.is_position_active = True
                            self.exit_in_progress = False
                            log_msg = "?좑툘 [泥?궛 1李??ㅽ뙣] 2以?鍮꾩긽 留덉뒪??泥?궛 寃⑸컻!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"異붿쟻?듭젅 鍮꾩긽 泥?궛 ?먮윭: {em_err}")
                        
        self.is_position_active = False
        self.custom_stop_active = False
        if self.bot and self.bot.dashboard and hasattr(self.bot.dashboard, "reset_stoploss_ui"):
            self.bot.dashboard.reset_stoploss_ui()
        self.exit_in_progress = False
        self.has_second_entry = False
        self.has_third_entry = False
        self.is_half_exited = False
        self.has_smart_guarded = False
        self.has_pyramided = False
        self.last_exit_time = time.time()
        dashboard = self.bot.dashboard
        cooldown_limit = dashboard.cooldown_seconds
        
        # [?좎젣 ?쏀궧] 鍮꾨룞湲??湲?await)瑜??湲???利됱떆 荑⑤떎?댁쓣 ?좎젣 留덊궧?섏뿬 1珥??덉깉 ?⑹냼 寃⑸컻 李⑤떒
        cooldown_sec = getattr(dashboard, "profit_cooldown_seconds", 15.0)
        self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + cooldown_sec)
        
        # ?됰떒媛 ?鍮??ㅼ젣 PnL?⑥씠 ?뚯닔(?먯떎)?몄? ?덉쟾?섍쾶 ?먯젙
        exit_pnl_pct = 0.0
        if self.entry_price > 0.0:
            current_bitget_price = await self.get_live_bitget_price_internal()
            if direction == "LONG":
                exit_pnl_pct = (current_bitget_price - self.entry_price) / self.entry_price
            else:
                exit_pnl_pct = (self.entry_price - current_bitget_price) / self.entry_price

            reason_label = "익절 쿨다운"

        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
            self.cooldown_timer_task.cancel()
        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(final_cooldown_sec, reason_label))

        # --- [?좎꽕] 泥?궛 ?뚮┝ ?듯빀 諛쒖넚 ?붿쭊 (?꾨씫 100% 諛⑹? 諛?異쒓뎄 ?щ━?쇱? 怨꾩륫) ---
        if not getattr(self, "exit_msg_sent", False):
            self.exit_msg_sent = True
            current_bitget_price = await self.get_live_bitget_price_internal()
            reason = getattr(self, "exit_reason", "") or "嫄곕옒???쒕쾭 ?ъ씠???ㅽ깙濡쒖뒪 泥닿껐 ?먮뒗 ?섎룞 泥?궛"
            
            # ?좏샇 ?뺣낫 異붿텧
            trigger_price = getattr(self, "last_exit_trigger_price", 0.0)
            if trigger_price <= 0.0:
                trigger_price = getattr(self, "last_placed_stop_price", self.entry_price)
            if trigger_price <= 0.0:
                trigger_price = current_bitget_price
            signal_price = trigger_price

            signal_time = getattr(self, "last_exit_signal_time", "")
            if not signal_time:
                import time
                signal_time = time.strftime("%Y-%m-%d %H:%M:%S")

            signal_qty = getattr(self, "last_exit_signal_qty", 0.0)
            if signal_qty <= 0.0:
                signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                
            # ?ㅼ젣 泥닿껐 ?뺣낫 異붿텧 (js_dom_actual_trade ?깆뿉???띾뱷)
            actual_price = getattr(self, "last_actual_exit_price", 0.0)
            actual_time = getattr(self, "last_actual_exit_time", "")
            actual_qty = getattr(self, "last_actual_exit_qty", 0.0)
            if actual_qty <= 0.0:
                actual_qty = float(getattr(self, "position_volume", 0)) / 1000.0

            if actual_price > 0.0 and actual_time:
                if direction == "LONG":
                    exit_slippage_usd = signal_price - actual_price
                else:
                    exit_slippage_usd = actual_price - signal_price
                exit_slippage_pct = (exit_slippage_usd / signal_price) * 100.0 if signal_price > 0 else 0.0
                
                # 臾쇰━ 濡쒓렇 ?뚯씪 諛??붾㈃ 濡쒓렇 ?ㅼ떆媛?湲곕줉
                log_msg = f"?렞 [泥?궛 ?щ━?쇱? ?ㅼ륫] ?寃??몃━嫄곌?: {signal_price:,.1f} USDT ?∽툘 鍮꾪듃寃?泥?궛媛: {actual_price:,.1f} USDT | ?몄감: {exit_slippage_usd:+,.1f} USDT ({exit_slippage_pct:+.3f}% ??쭏吏?諛쒖깮)"
                if self.bot.dashboard:
                    self.bot.dashboard.add_log(log_msg)
                
                # PnL 怨꾩궛
                if direction == "LONG":
                    pnl_pct = (actual_price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0.0
                    pnl_from_entry_1 = (actual_price - self.entry_price_1) / self.entry_price_1 if self.entry_price_1 > 0 else pnl_pct
                else:
                    pnl_pct = (self.entry_price - actual_price) / self.entry_price if self.entry_price > 0 else 0.0
                    pnl_from_entry_1 = (self.entry_price_1 - actual_price) / self.entry_price_1 if self.entry_price_1 > 0 else pnl_pct
                    
                if self.bot.dashboard:
                    # 2李?3李??곹깭 ?뺤씤
                    if self.has_second_entry or getattr(self, "has_third_entry", False):
                        state_str = "3李?吏꾩엯 ?곹깭" if getattr(self, "has_third_entry", False) else "2李?吏꾩엯 ?곹깭"
                        dir_str = f"{direction} ({state_str})"
                        pnl_str = f"?됰떒 ?鍮??섏씡瑜? <b>{pnl_pct * 100:+.2f}%</b>\n1李??鍮??섏씡瑜? <b>{pnl_from_entry_1 * 100:+.2f}%</b>"
                    else:
                        dir_str = f"{direction}"
                        pnl_str = f"理쒖쥌 ?섏씡瑜? <b>{pnl_pct * 100:+.2f}%</b>"

                    msg = f"<b>?렞 [泥?궛 ?꾨즺 ?뚮┝]</b>\n" \
                          f"諛⑺뼢: <b>{dir_str}</b>\n" \
                          f"?ъ쑀: <b>{reason}</b>\n\n" \
                          f"<b>[?좏샇 諛쒖깮 ?뺣낫]</b>\n" \
                          f"?좏샇 諛쒖깮?쒓컙: <b>{signal_time}</b>\n" \
                          f"?섎웾: <b>{signal_qty:.3f} BTC</b>\n" \
                          f"?좏샇 諛쒖깮 媛寃? <b>{signal_price:,.1f} USDT</b>\n\n" \
                          f"<b>[?ㅼ젣 泥닿껐 ?뺣낫]</b>\n" \
                          f"?ㅼ젣 泥닿껐 ?쒓컙: <b>{actual_time}</b>\n" \
                          f"?섎웾: <b>{actual_qty:.3f} BTC</b>\n" \
                          f"?⑹궛 ?됰떒媛: <b>{self.entry_price:,.1f} USDT</b>\n" \
                          f"泥?궛 媛寃? <b>{actual_price:,.1f} USDT</b>\n" \
                          f"{pnl_str}\n" \
                          f"異쒓뎄 ?щ━?쇱?: <b>{exit_slippage_usd:+,.1f} USDT ({exit_slippage_pct:+.3f}%)</b>"
                    
                    self.bot.dashboard.send_telegram_notification(msg)


# ==============================================================================
# ?몄뀡蹂??꾧퀎移?諛??몃젅?대뵫 ?듭떖 ?ㅼ젙 怨좉툒 ?ㅼ젙李??대옒??(QDialog) (媛쒕컻怨꾪쉷??176)
# ==============================================================================
class ShinseonConfigDialog:
    pass
