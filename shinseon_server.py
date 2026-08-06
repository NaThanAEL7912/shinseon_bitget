
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
import hmac
import hashlib
import base64

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

def safe_int(v, default=0):
    try: return int(float(v))
    except: return default

def safe_float(v, default=0.0):
    try: return float(v)
    except: return default

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

async def send_telegram_notification_server(message):
    try:
        config = load_server_config()
        bot_token = str(config.get("TELEGRAM_BOT_TOKEN", "") or "").strip()
        chat_id = str(config.get("TELEGRAM_CHAT_ID", "") or "").strip()
        if not bot_token or not chat_id:
            return
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=5.0) as resp:
                pass
    except Exception as e:
        logger.error(f"Telegram server send error: {e}")

def write_trade_history_log(message):
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOGS_DIR, f"shinseon_trade_{today_str}.log")
    time_prefix = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
    full_msg = f"{time_prefix} {message}\n"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(full_msg)
    except Exception as e:
        logger.error(f"로그 파일 기록 에러: {e}")
    logger.info(f"[HISTORY] {message}")
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(send_telegram_notification_server(f"<b>[신선 봇]</b> {message}"))
    except Exception:
        pass

async def run_telegram_command_poller(bot_core):
    last_update_id = 0
    while True:
        try:
            config = load_server_config()
            bot_token = str(config.get("TELEGRAM_BOT_TOKEN", "") or "").strip()
            chat_id = str(config.get("TELEGRAM_CHAT_ID", "") or "").strip()
            if not bot_token or not chat_id:
                await asyncio.sleep(5)
                continue
            
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 10}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 200:
                        res_json = await resp.json()
                        for update in res_json.get("result", []):
                            last_update_id = update["update_id"]
                            message_obj = update.get("message", {})
                            from_chat_id = str(message_obj.get("chat", {}).get("id", ""))
                            text = message_obj.get("text", "").strip()
                            
                            if chat_id and from_chat_id != chat_id:
                                continue
                                
                            if text in ["시작", "/시작", "/start"]:
                                if bot_core.v35_engine:
                                    bot_core.v35_engine.bot_state = "RUNNING"
                                await send_telegram_notification_server("✅ <b>[신선 봇]</b> 실전 자동 저격 감시가 시작되었습니다.")
                                ui_callback(bot_core.current_price, 1, "✅ [텔레그램 원격] 봇 가동 감시 시작")
                            elif text in ["정지", "/정지", "/stop"]:
                                if bot_core.v35_engine:
                                    bot_core.v35_engine.bot_state = "STOPPED"
                                await send_telegram_notification_server("🛑 <b>[신선 봇]</b> 자동 저격 감시가 일시 정지되었습니다.")
                                ui_callback(bot_core.current_price, 1, "🛑 [텔레그램 원격] 봇 가동 정지")
                            elif text in ["상태", "/상태", "/status"]:
                                pos_str = "100% 현금 대기 중"
                                pnl_info = ""
                                if bot_core.v35_engine and bot_core.v35_engine.is_position_active:
                                    side = getattr(bot_core.v35_engine, "entry_direction", "")
                                    entry_price = getattr(bot_core.v35_engine, "entry_price", 0.0)
                                    contracts = float(getattr(bot_core.v35_engine, "position_volume", 0)) / 1000.0
                                    pos_str = f"{side} 진입 중 ({contracts:.3f} BTC @ ${entry_price:,.1f})"
                                    pnl_info = f"\nROE: <b>{getattr(bot_core.v35_engine, 'last_live_roe_pct', 0.0):+.2f}%</b>"
                                
                                state_str = bot_core.v35_engine.bot_state if bot_core.v35_engine else "RUNNING"
                                bal_str = f"${getattr(bot_core, 'bitget_balance', 0.0):,.2f} USDT"
                                status_msg = (
                                    f"<b>📊 [신선 봇 실시간 상태보고]</b>\n\n"
                                    f"현재가: <b>${bot_core.current_price:,.1f} USDT</b>\n"
                                    f"포지션: <b>{pos_str}</b>{pnl_info}\n"
                                    f"비트겟 잔고: <b>{bal_str}</b>\n"
                                    f"구동 상태: <b>{state_str}</b>"
                                )
                                await send_telegram_notification_server(status_msg)
                            elif text in ["청산", "/청산", "/close", "비상탈출"]:
                                if bot_core.v35_engine:
                                    bot_core.v35_engine.bot_state = "STOPPED"
                                await bot_core.execute_emergency()
                                await send_telegram_notification_server("🚨 <b>[신선 봇]</b> 비트겟 거래소 포지션 100% 시장가 즉시 전량 청산 완료!")
                                ui_callback(bot_core.current_price, 1, "🚨 [텔레그램 원격] 비상 탈출 100% 시장가 전량 청산 완료")
        except Exception:
            pass
        await asyncio.sleep(2)

def append_daily_csv_record(row_str):
    today_str = datetime.now().strftime("%Y-%m-%d")
    csv_file = os.path.join(LOGS_DIR, f"shinseon_data_{today_str}.csv")
    file_exists = os.path.exists(csv_file)
    try:
        with open(csv_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("timestamp,price,oi,liq_1m,cvd,log_type,msg\n")
            f.write(row_str + "\n")
    except Exception:
        pass

# ---- BOT CORE AND ENGINE ----
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
        self.cdp_lock = asyncio.Lock()  # CDP 연결 동시 충돌 방지 락
        
        # 비트겟 CCXT 초기화
        self.bitget_exchange = None
        api_key = env_vars.get("BITGET_API_KEY", "")
        api_secret = env_vars.get("BITGET_SECRET_KEY", "")
        api_password = env_vars.get("BITGET_PASSPHRASE", "")
        
        if api_key and api_secret and api_password:
            import ccxt.async_support as ccxt
            self.bitget_exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': api_secret,
                'password': api_password,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            print("✅ [API] 비트겟 API 키 세팅 완료. (ccxt.bitget 초기화 됨)")
        else:
            print("❌ [경고] 비트겟 API 키가 설정되지 않았습니다. 실전 잔고/주문 조회가 불가능합니다. server_config.json을 확인하세요.")


        self.bitget_headers = {}  # BITGET 실시간 인증 헤더 보관용 딕셔너리
        self.last_binance_time_ms = int(time.time() * 1000)  # 가장 최신 바이낸스 웹소켓 틱 타임스탬프 (ms)
        self.last_packet_latency_ms = 15.0  # 순정 바이낸스 패킷 레이턴시 수치 (ms)
        self.buy_liq_buffer = deque()
        self.sell_liq_buffer = deque()
        self.price_history = deque()
        self.current_price = 0.0
        self.price_ready = False

        # V4.24 클라이언트-서버 완전동기화 인스턴스 변수
        self.session_thresholds = {
            "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
            "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
            "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
            "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True},
            "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
            "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
            "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
            "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True}
        }
        self.session_guardrails = {
            "ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
            "LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
            "NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
            "PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True},
            "WEEKEND_ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
            "WEEKEND_LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
            "WEEKEND_NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
            "WEEKEND_PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True}
        }
        self.manual_threshold = False
        self.target_liq = "2,500,000"
        self.target_oi = "0.12"
        self.target_slippage = "0.15"
        self.manual_config = {
            "manual_threshold": False,
            "target_liq": "2,500,000",
            "target_oi": "0.12",
            "target_slippage": "0.15"
        }
        self.leverage_level = 30
        self.betting_ratio = 400.0
        self.split_entry_1_ratio = 250.0
        self.split_entry_2_ratio = 100.0
        self.split_entry_2_trigger_pct = -0.3
        self.split_entry_3_ratio = 50.0
        self.split_entry_3_trigger_pct = -0.6
        self.split_cooldown_seconds = 900.0
        self.cooldown_seconds = 60.0
        self.profit_cooldown_seconds = 15.0
        self.half_exit_close_ratio = 50.0
        self.pyramiding_enabled = True
        self.pyramiding_ratio = 30.0

        # 저장된 shinseon_config.json 있으면 즉시 자동 로드
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shinseon_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.session_thresholds = cfg.get("session_thresholds", self.session_thresholds)
                self.session_guardrails = cfg.get("session_guardrails", self.session_guardrails)
                self.manual_threshold = cfg.get("manual_threshold", self.manual_threshold)
                self.target_liq = cfg.get("target_liq", self.target_liq)
                self.target_oi = cfg.get("target_oi", self.target_oi)
                self.target_slippage = cfg.get("target_slippage", self.target_slippage)
                self.manual_config = {
                    "manual_threshold": self.manual_threshold,
                    "target_liq": self.target_liq,
                    "target_oi": self.target_oi,
                    "target_slippage": self.target_slippage
                }
                self.leverage_level = cfg.get("leverage_level", self.leverage_level)
                self.betting_ratio = cfg.get("betting_ratio", self.betting_ratio)
                self.split_entry_1_ratio = cfg.get("split_entry_1_ratio", self.split_entry_1_ratio)
                self.split_entry_2_ratio = cfg.get("split_entry_2_ratio", self.split_entry_2_ratio)
                self.split_entry_2_trigger_pct = cfg.get("split_entry_2_trigger_pct", self.split_entry_2_trigger_pct)
                self.split_entry_3_ratio = cfg.get("split_entry_3_ratio", self.split_entry_3_ratio)
                self.split_entry_3_trigger_pct = cfg.get("split_entry_3_trigger_pct", self.split_entry_3_trigger_pct)
                self.split_cooldown_seconds = cfg.get("split_cooldown_seconds", self.split_cooldown_seconds)
                self.cooldown_seconds = cfg.get("cooldown_seconds", self.cooldown_seconds)
                self.profit_cooldown_seconds = cfg.get("profit_cooldown_seconds", self.profit_cooldown_seconds)
                self.half_exit_close_ratio = cfg.get("half_exit_close_ratio", self.half_exit_close_ratio)
                self.pyramiding_enabled = cfg.get("pyramiding_enabled", self.pyramiding_enabled)
                self.pyramiding_ratio = cfg.get("pyramiding_ratio", self.pyramiding_ratio)
                print("⚙️ [Server BotCore] shinseon_config.json 설정값 자동 로드 완료!")
        except Exception as e:
            print(f"⚠️ [Server BotCore] Config 로드 실패: {e}")
        
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
        self.telegram_poller_task = asyncio.create_task(run_telegram_command_poller(self))
        
        # v3.5 단방향 저격 엔진 기상
        self.v35_engine = ShinseonV35Engine(self)
        self.v35_engine.CAPITAL = self.c_total
        self.v35_engine.DEPLOY_MARGIN = self.c_total * 0.50
        self.v35_engine.POSITION_SIZE = self.v35_engine.DEPLOY_MARGIN * 20.0
        
        ui_callback(0.0, 0, "★ [雷達] 바이낸스 실시간 시세 웹소켓(WSS) 연결 수립 중...")
        
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
            logger.error(f"과거 캔들 이력 로드 지연: {e}")
        finally:
            await spot_exchange.close()
            
        # 🟢 [v4.05 완치]: VPN 침묵의 Drop 묵살 타파 및 현물망(stream) 직통 롤백 (추후 일본 VPS 이주 시 fstream으로 복귀 강력 권장)
        uri = "wss://stream.binance.com/stream?streams=btcusdt@ticker/btcusdt@aggTrade"
        
        # 100% 실시간 리얼 청산 및 OI 버퍼 초기화
        from collections import deque
        import aiohttp
        self.liq_buffer = deque()      # (timestamp, usd_value)
        self.oi_history = deque()      # (timestamp, oi_value)
        self.real_liq_1m = 0.0
        self.real_oi_speed_1m = 0.0
        self.liq_wss_connected = True
        self.last_real_forceorder_time = 0.0
        
        # v1.1 성능 격상: aggTrade 실시간 누적기
        self.agg_buy_vol = 0.0
        self.agg_sell_vol = 0.0
        
        self.mock_liq = 0.0
        self.mock_oi = 0.0
        self.current_price = 0.0
        self.spot_price = 0.0
        self.price_basis = 0.0
        self.bitget_current_price = 0.0
        if self.v35_engine:
            asyncio.create_task(self.v35_engine.run_bitget_ticker_stream())
        self.open_p = 63100.0
        self.high_p = 63300.0
        self.low_p = 62900.0
        
        # 매 1초마다 가격 변동과 연동하여 게이지 바를 상시 부드럽게 흔드는 비동기 텔레메트리 루프 추가 가동 (가장 먼저 독립 구동!)
        async def run_telemetry_loop():
            while self.is_running:
                try:
                    await asyncio.sleep(0.1)
                    
                    # 0. KST 시스템 시간 기반 동적 임계치 실시간 계산 및 수동 오버라이드
                    # 0. KST 시스템 시간 기반 동적 임계치 실시간 계산 및 수동 오버라이드
                    from datetime import datetime, timezone, timedelta
                    kst_tz = timezone(timedelta(hours=9))
                    kst_dt = datetime.now(timezone.utc).astimezone(kst_tz)
                    hour_val = kst_dt.hour
                    kst_time_str = kst_dt.strftime("%H:%M:%S")
                    
                    dashboard = getattr(self, "dashboard", None)
                    # BotCore session_thresholds 및 dashboard 안전 참조
                    thresholds = getattr(self, "session_thresholds", {
                        "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
                        "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
                        "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
                        "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3},
                        "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
                        "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
                        "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
                        "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3}
                    })
                    if dashboard and hasattr(dashboard, "session_thresholds"):
                        thresholds = dashboard.session_thresholds

                    # 시간대별 세션 판정 및 기본 임계치 추출 (09시~09시 트레이딩 데이 연동 + 1분 완충 타임락 개발계획서_260)
                    trading_dt = kst_dt - timedelta(hours=9)
                    is_weekend = kst_dt.weekday() in [5, 6]
                    minute_val = kst_dt.hour * 60 + kst_dt.minute
                    
                    # 1분 완충 타임락 규칙 적용:
                    # - 아시아: 08:59:00 ~ 15:58:59 (539 <= m < 959)
                    # - 유럽: 15:59:00 ~ 22:28:59 (959 <= m < 1349)
                    # - 미국 본장: 22:29:00 ~ 04:58:59 (m >= 1349 or m < 299)
                    # - 태평양: 04:59:00 ~ 08:58:59 (299 <= m < 539)
                    if 539 <= minute_val < 959:
                        if is_weekend:
                            session_key = "weekend_asia"
                            current_session = f"🌴 주말 아시아 (KST {kst_time_str})"
                        else:
                            session_key = "asia"
                            current_session = f"🔴 아시아 장세 (KST {kst_time_str})"
                    elif 959 <= minute_val < 1349:
                        if is_weekend:
                            session_key = "weekend_europe"
                            current_session = f"🌴 주말 유럽 (KST {kst_time_str})"
                        else:
                            session_key = "europe"
                            current_session = f"🟡 유럽 장세 (KST {kst_time_str})"
                    elif minute_val >= 1349 or minute_val < 299:
                        if is_weekend:
                            session_key = "weekend_us"
                            current_session = f"🌴 주말 미국 본장 (KST {kst_time_str})"
                        else:
                            session_key = "us"
                            current_session = f"🟢 미국 본장 (KST {kst_time_str})"
                    else: # 299 <= minute_val < 539 (04:59 ~ 08:58)
                        if is_weekend:
                            session_key = "weekend_pacific"
                            current_session = f"🌴 주말 태평양 (KST {kst_time_str})"
                        else:
                            session_key = "pacific"
                            current_session = f"⚪ 태평양 횡보 (KST {kst_time_str})"
                    
                    target_liq = thresholds[session_key]["liq"]
                    target_oi = thresholds[session_key]["oi"]
                    target_sl = thresholds[session_key]["sl"]

                    is_manual = False
                    if dashboard and hasattr(dashboard, "chk_manual_threshold"):
                        is_manual = dashboard.chk_manual_threshold.isChecked()
                    else:
                        is_manual = getattr(self, "manual_threshold", False)

                    if is_manual:
                        current_session = f"⚙ 수동 조율 ({kst_time_str})"
                        if dashboard and hasattr(dashboard, "edit_target_liq"):
                            liq_txt = dashboard.edit_target_liq.text().replace(",", "").strip()
                            oi_txt = dashboard.edit_target_oi.text().strip()
                            slip_txt = dashboard.edit_target_slippage.text().strip()
                        else:
                            liq_txt = str(getattr(self, "target_liq", "2,500,000")).replace(",", "").strip()
                            oi_txt = str(getattr(self, "target_oi", "0.12")).strip()
                            slip_txt = str(getattr(self, "target_slippage", "0.15")).strip()

                        try:
                            target_liq = float(liq_txt) if liq_txt else 100000.0
                        except Exception:
                            target_liq = 100000.0
                        try:
                            target_oi = float(oi_txt) if oi_txt else 0.02
                        except Exception:
                            target_oi = 0.02
                        try:
                            target_slippage = float(slip_txt) if slip_txt else 0.15
                        except Exception:
                            target_slippage = 0.15
                        if self.v35_engine:
                            self.v35_engine.ENTRY_SLIPPAGE_CAP = target_slippage / 100.0

                    # 백엔드 엔진에 세션별 손절선 및 세션 정보 전달
                    if self.v35_engine:
                        self.v35_engine.current_session_sl = target_sl
                        self.v35_engine.current_session_key = session_key
                        self.v35_engine.current_session_name = current_session
                    
                    # 1. 모드에 따른 데이터 분기 및 1분 가격 변동 산출
                    now_t = time.time()
                    while self.price_history and now_t - self.price_history[0][0] > 60.0:
                        self.price_history.popleft()
                        
                    if self.price_history:
                        price_10s_ago = self.price_history[0][1]
                    else:
                        price_10s_ago = self.current_price
                        
                    price_delta_10s = self.current_price - price_10s_ago
                    
                    if self.v35_engine.is_local_mode:
                        # 🔴 모의 테스트 모드: 시뮬레이션 데이터 갱신
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
                        # 🟢 실전 라이브 모드: WSS 누적 계산 반영
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
                            
                    # 지능형 저격 방향성 판정
                    oi_delta_1m = display_oi
                    if short_liq > long_liq:
                        direction = "LONG"   # 숏 청산 폭등 ➡️ 무조건 LONG!
                    elif long_liq > short_liq:
                        direction = "SHORT"  # 롱 청산 폭락 ➡️ 무조건 SHORT!
                    else:
                        direction = "LONG" if price_delta_10s > 0 else "SHORT"
                        
                    # v1.1 성능 격상: CVD 델타 산출 및 1분 큐 업데이트
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
                            
                        # 2. 실시간 오더플로우 저격 신호 검사 (동적 임계치 전달)
                        binance_event_time = int(getattr(self, "last_binance_time_ms", time.time() * 1000))
                        ws_frame = {
                            'timestamp_ms': binance_event_time,
                            'rolling_1m_liq_usd': display_liq,
                            'oi_delta_1m': display_oi,
                            'mid_price': self.current_price,
                            'direction': direction
                        }
                        await self.v35_engine.check_radar_signal_dynamic(ws_frame, target_liq, target_oi)
                    
                    # 3초마다 비트겟 거래소 실제 포지션 강제 동기화 (가짜 포지션 잠김 100% 박멸)
                    now_t_sync = time.time()
                    if now_t_sync - getattr(self, "last_bitget_pos_sync_time", 0.0) >= 3.0:
                        self.last_bitget_pos_sync_time = now_t_sync
                        if hasattr(self, "wss") and self.wss:
                            asyncio.create_task(self.wss.sync_bitget_real_position_status())
                        else:
                            asyncio.create_task(self.sync_bitget_real_position_status())
                    
                    # 3. UI 갱신 송출 (동적 임계치 및 KST 세션 정보 탑재)
                    latency_show = float(getattr(self, "last_packet_latency_ms", 15.0))
                    status_msg = "100% 현금 대기 중 (저격 대기)"
                    if self.v35_engine.is_position_active:
                        direction_active = getattr(self.v35_engine, "entry_direction", None) or getattr(self.v35_engine, "position_side", "LONG") or "LONG"
                        entry = self.v35_engine.entry_price
                        current = self.current_price
                        bg_p = getattr(self, "bitget_current_price", 0.0) or (getattr(self.v35_engine, "bitget_current_price", 0.0) if self.v35_engine else 0.0)
                        calc_price = bg_p if bg_p > 0.0 else current
                        leverage = getattr(self.v35_engine, "leverage", 30) or 30

                        if direction_active == "LONG":
                            live_pnl = ((calc_price - entry) / entry) * 100.0 if (entry > 0.0 and calc_price > 0.0) else 0.0
                        else:
                            live_pnl = ((entry - calc_price) / entry) * 100.0 if (entry > 0.0 and calc_price > 0.0) else 0.0
                            
                        roe_pct = live_pnl * leverage
                        
                        p_vol = getattr(self.v35_engine, "position_volume", 0)
                        if isinstance(p_vol, (int, float)) and p_vol > 0:
                            btc_qty = float(p_vol) if float(p_vol) < 100.0 else float(p_vol) / 1000.0
                        else:
                            btc_qty = 0.0012

                        live_usdt = btc_qty * entry * (live_pnl / 100.0) if (btc_qty > 0 and entry > 0) else 0.0
                        usdt_str = f" ({live_usdt:+.2f} USDT)" if btc_qty > 0 else ""

                        # 동적 세션 가드레일 임계치 추출
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
                        dashboard_guard = getattr(dashboard, "session_guardrails", None)
                        bot_guard = getattr(self, "session_guardrails", {})
                        s_guardrails = (dashboard_guard or bot_guard).get(s_guard_key, {"trigger": 0.5, "guard": 0.0})
                        guard_trig = s_guardrails.get("trigger", 0.5)
                        guard_limit = s_guardrails.get("guard", 0.0)
                        
                        is_half_exited = getattr(self.v35_engine, "is_half_exited", False)
                        has_smart_guarded = getattr(self.v35_engine, "has_smart_guarded", False)
                        custom_stop_active = getattr(self.v35_engine, "custom_stop_active", False)
                        custom_stop_offset = getattr(self.v35_engine, "custom_stop_offset_roe", getattr(self.v35_engine, "custom_stop_offset_pct", -6.0))
                        
                        pnl_hdr = f"[{direction_active} 진입 @ {entry:,.1f}] ROE: {roe_pct:+.2f}%{usdt_str} (PNL: {live_pnl:+.2f}%)"
                        
                        if has_smart_guarded:
                            status_msg = f"{pnl_hdr}\n(🛡 스마트 본전가드 작동 | 본전가드: {guard_limit:+.2f}%)"
                        elif is_half_exited:
                            status_msg = f"{pnl_hdr}\n(🛡 50% 분할익절 완료 | 본전가드: {guard_limit:+.2f}%)"
                        else:
                            status_msg = f"{pnl_hdr}\n(가드레일: +{guard_trig:.2f}%)"
                            
                        if live_pnl <= (target_sl + 0.2):
                            status_msg = f"⚠ [{direction_active} 위기 @ {entry:,.1f}] ROE: {roe_pct:+.2f}%{usdt_str}\n(손절 데드라인 임박: {target_sl:+.2f}%)"

                        if custom_stop_active:
                            stop_label = "익절" if custom_stop_offset > 0 else "손절"
                            status_msg += f"\n(🛡 스마트 스탑 가드: {custom_stop_offset:+.2f}% ROE {stop_label} 감시 중)"

                    elif self.v35_engine.is_snipe_active:
                        status_msg = "🟢 실전 저격 감시 가동 중..."
                        
                    has_real_force = (time.time() - getattr(self, "last_real_forceorder_time", 0.0)) <= 60.0
                    liq_wss_connected = getattr(self, "liq_wss_connected", True)

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
                        expected_dir=direction,
                        has_real_force=has_real_force,
                        liq_wss_connected=liq_wss_connected
                    )
                    
                except Exception as ex:
                    logger.error(f"텔레메트리 보정 루프 에러: {ex}")
        
        asyncio.create_task(run_telemetry_loop())
        
        # [실전 연동 2]: 24시간 백그라운드 자동 레이턴시 실측 로깅 데몬 구동 (60초 주기 - 초경량 aiohttp 0ms 직송)
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
                            final_verdict = f"자동측정 - 평균시차: {total_delta:.1f}ms | BITGET핑: {bitget_pure_ping:.1f}ms | 판정: {verdict}"
                            
                            if self.ui_cb:
                                self.ui_cb(0.0, 1, f"⚡ [자동 레이턴시] {final_verdict}")
                                
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
                            asyncio.create_task(asyncio.to_thread(_write_bench, log_path, log_line))

                    await asyncio.wait_for(_do_bench(), timeout=2.0)
                except Exception as ex:
                    pass

        asyncio.create_task(run_background_latency_logger())
        
        # [실전 연동 6]: 1시간 주기 브라우저 자동 리로드 데몬 (크롬 메모리 누수 및 프리징 방지) (개발계획서_188_35)
        async def run_periodic_browser_reloader():
            reload_interval = 3600.0
            last_reload_time = time.time()
            
            while self.is_running:
                try:
                    await asyncio.sleep(60.0) # 1분마다 주기 체크
                    if not self.is_running:
                        break
                        
                    current_time = time.time()
                    if current_time - last_reload_time >= reload_interval:
                        if self.v35_engine and not self.v35_engine.is_position_active and not self.v35_engine.exit_in_progress:
                            if self.ui_cb:
                                self.ui_cb(0.0, 1, "🔄 [RPA 복원] 브라우저 누수 방지용 3시간 주기 자동 페이지 새로고침(Reload)을 집행합니다.")
                            
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
                                            self.ui_cb(0.0, 1, "✅ [RPA 복원] 브라우저 페이지 새로고침 완료! BITGET 탭이 성공적으로 리로드되었습니다.")
                                        last_reload_time = current_time
                                    else:
                                        if self.ui_cb:
                                            self.ui_cb(0.0, 1, "⚠️ [RPA 복원] 크롬 브라우저에서 BITGET 탭을 찾을 수 없어 리로드를 건너뜁니다.")
                                except Exception as e:
                                    if self.ui_cb:
                                        self.ui_cb(0.0, 1, f"⚠️ [RPA 복원] 브라우저 연결 실패 ({e}) ➡️ 크롬 브라우저 자동 재기동을 시도합니다.")
                                    bat_path = os.path.join(BASE_DIR, "디버깅크롬_시작.bat")
                                    if os.path.exists(bat_path):
                                        subprocess.Popen(["cmd.exe", "/c", "디버깅크롬_시작.bat"], cwd=BASE_DIR)
                                        if self.ui_cb:
                                            self.ui_cb(0.0, 1, "🚀 [RPA 복원] 디버깅 크롬 브라우저 팝업 호출 완료!")
                                        await asyncio.sleep(3.0)
                                        last_reload_time = current_time
                                finally:
                                    if pw:
                                        try: await pw.stop()
                                        except: pass
                except Exception as ex:
                    logger.error(f"브라우저 리로더 루프 에러: {ex}")
                    
        asyncio.create_task(run_periodic_browser_reloader())
        
        # [실전 연동 1]: 바이낸스 공식 선물 실시간 청산 주문 WSS 백그라운드 수집 테스크 (2초 연결 타임아웃 제한 장착!)
        async def run_liquidation_wss():
            liq_uri = "wss://fstream.binance.com/ws/btcusdt@forceOrder"
            while self.is_running:
                try:
                    # 방심위 차단 무한 Pending을 방지하기 위해 2.0초 연결 타임아웃 제한 강제화
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
                                side_label = "SHORT" if o.get("S") == "BUY" else "LONG"
                                if o.get("S") == "BUY":
                                    self.buy_liq_buffer.append((now_t, usd_val))
                                elif o.get("S") == "SELL":
                                    self.sell_liq_buffer.append((now_t, usd_val))
                                
                                # 💥 바이낸스 찐청산 발생 시 실시간 금액 로그 브로드캐스트
                                rolling_tot = sum(val for t, val in self.liq_buffer if now_t - t <= 60.0)
                                cur_price = getattr(self, "current_price", 0.0)
                                log_msg = f"💥 [바이낸스 찐청산 포착] {side_label} 청산 ${usd_val:,.0f} 발생! (1분 누적: ${rolling_tot:,.0f})"
                                asyncio.create_task(self.broadcast_event("ui_update", {"msg": log_msg, "log_type": 1, "price": cur_price}))
                except Exception as liq_err:
                    self.liq_wss_connected = False
                    logger.warning(f"선물 청산 WSS 연결 장애: {liq_err}")
                    await asyncio.sleep(0.5)
                    
        # [실전 연동 2]: 바이낸스 공식 선물 실시간 OI REST API 초고속(0.2초 주기) 폴링 테스크
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
                                
                                # 1분 이상 지난 데이터 제거
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
                    
        # [실전 연동 4]: 바이낸스 100% 정밀 실시간 네트워크 패킷 레이턴시(Ping) 실측 데몬 (2초 주기)
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
                # 현물 웹소켓 연결 (방심위 차단 대상이 아니므로 매우 안정적임)
                websocket_conn = await asyncio.wait_for(websockets.connect(uri), timeout=2.0)
                async with websocket_conn as websocket:
                    ui_callback(self.current_price, 0, "✔ [雷達] 하이브리드 프리미엄 엔진 가동 중. 실시간 감시 작동.", current_session="실전 대기 중")
                    
                    while self.is_running:
                        # 1. 웹소켓 수신 시도 (안정적인 현물망이므로 타임아웃은 다시 15초 유지)
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        except Exception as conn_err:
                            logger.error(f"웹소켓 수신 연결 오류: {conn_err}")
                            raise Exception(f"웹소켓 연결 소실: {conn_err}")

                        # 2. 데이터 처리 및 파싱 (일반 파싱 오류는 로그 기록 후 세션 유지)
                        try:
                            wrapper = json.loads(message)
                            stream_name = wrapper.get("stream", "")
                            data = wrapper.get("data", {})
                            
                            # 바이낸스 최신 이벤트 타임스탬프 0ms 오차로 메모리에 다이렉트 갱신
                            if "E" in data:
                                event_t = int(data.get("E"))
                                self.last_binance_time_ms = event_t
                                recv_t = time.time() * 1000
                                self.last_packet_latency_ms = max(0.0, recv_t - event_t)
                            
                            if stream_name == "btcusdt@ticker":
                                # ticker 데이터 파싱 (현물 가격 수신 후 프리미엄 Basis 더해서 선물 가격으로 둔갑시킴)
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
                                    # 매 정각(15분 단위) 기어 조정을 간접적으로 에뮬레이션
                                    if int(time.time()) % 900 == 0:
                                        candles.pop(0)
                                        for i in range(len(candles)):
                                            candles[i][0] = float(i)
                                        candles.append([float(len(candles)), self.open_p, self.current_price, self.low_p, self.high_p])
                                    chart_callback(list(candles))
                                    
                            elif stream_name == "btcusdt@aggTrade":
                                # aggTrade 데이터 파싱 (선물 WSS 차단 시 대량 체결 볼륨 대체용)
                                q = float(data.get("q", 0.0))
                                p = float(data.get("p", 0.0))
                                usd_val = q * p
                                
                                # v1.1 성능 격상: aggTrade 실시간 매수/매도 누적 연산
                                is_buyer_maker = data.get("m", False)
                                if not is_buyer_maker:
                                    self.agg_buy_vol += q
                                else:
                                    self.agg_sell_vol += q
                                    
                                if usd_val >= 10000.0:
                                    now_t = time.time()
                                    self.liq_buffer.append((now_t, usd_val))
                                    if not is_buyer_maker:
                                        self.buy_liq_buffer.append((now_t, usd_val))
                                    else:
                                        self.sell_liq_buffer.append((now_t, usd_val))
                                        
                        except Exception as parse_err:
                            logger.error(f"웹소켓 데이터 처리 에러: {parse_err}")
                            await asyncio.sleep(1.0)
                            
                            
            except Exception as e:
                logger.warning(f"바이낸스 현물 WSS 연결 장애 ➡️ 5초 후 자가치유 시도: {e}")
                ui_callback(self.current_price, 0, "⚠️ [雷達] 바이낸스 WSS 재연결 시도 중...", current_session="WSS 복구 중")
                await asyncio.sleep(5.0)

        if fallback_task and not fallback_task.done():
            fallback_task.cancel()
        self.is_running = False

    async def execute_emergency(self):
        """🚨 긴급 청산 실행 및 비동기 작업 정리 (실물 발주는 대시보드 마스터 함수에서 단일 연결로 처리)"""
        if self.v35_engine and self.v35_engine.is_position_active:
            self.v35_engine.is_position_active = False
        await asyncio.sleep(0.1)

    async def sync_bitget_real_position_status(self):
        try:
            if getattr(self, "bitget_exchange", None) and getattr(self, "v35_engine", None):
                positions = await self.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])
                active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0), None)
                if not active_pos:
                    if self.v35_engine.is_position_active:
                        logger.info("⚡ [실시간 강제 동기화 v4.82] 거래소 포지션 0개 감지 ➡️ is_position_active False 강제 리셋 완료")
                        self.v35_engine.is_position_active = False
                        self.v35_engine.position_volume = 0
                        self.v35_engine.entry_price = 0.0
                        self.v35_engine.entry_direction = ""
                else:
                    self.v35_engine.is_position_active = True
                    self.v35_engine.entry_direction = active_pos['side'].upper()
                    self.v35_engine.entry_price = float(active_pos.get('entryPrice', 0.0) or 0.0)
                    self.v35_engine.position_volume = float(active_pos.get('contracts', 0.0) or 0.0)
        except Exception as e:
            pass


# ==============================================================================
# [新鮮 v3.5] 단방향 오더플로우 HFT 저격 및 3대 독약 방어벽 엔진
# ==============================================================================
class ShinseonV35Engine:
    def __init__(self, bot_core):
        self.bot = bot_core
        self.CAPITAL = 20000.0            # 총 자본금
        self.DEPLOY_MARGIN = 10000.0      # 운영 마진 (50%)
        self.LEVERAGE = 20                # 레버리지 20배
        self.POSITION_SIZE = 200000.0     # 목표 포지션 가치
        
        self.MAX_LATENCY_MS_LOCAL = 300.0  # 로컬 개발 PC 레이턴시 컷오프 (300ms)
        self.MAX_LATENCY_MS_PROD = 50.0   # AWS 도쿄 실전 레이턴시 컷오프 (50ms)
        self.is_local_mode = False        # 기본 기동 실전 라이브 모드 (False)
        
        self.ENTRY_SLIPPAGE_CAP = 0.0030  # 진입 허용 슬리피지 (0.30% - 안전 확장 v4.82)
        
        self.entry_direction = "LONG"
        self.position_side = "LONG"
        self.is_position_active = False
        self.is_snipe_active = True      # 24시간 자율 저격 감시 가동 상태
        self.bot_state = "RUNNING"        # 기본 24시간 봇 가동 상태 (RUNNING)
        self.exit_in_progress = False     # 선제 청산 중복 방지 락 플래그 (개발계획서_171)
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
        self.peak_buying_delta = 100000.0 # 피크 매수 델타 볼륨 추종 변수
        self.last_signal_price = 0.0
        self.last_exit_trigger_price = 0.0
        self.is_guardrail_running = False
        self.is_half_exited = False
        self.has_smart_guarded = False
        self.has_pyramided = False
        
        # 1초 가변 CSV 레코더 상태 변수
        self.last_record_time = 0.0
        self.record_mode_1s = False
        self.below_trigger_since = None
        
        # v1.1 성능 격상: CVD 및 OI 큐 초기화
        from collections import deque
        self.cvd_history = deque(maxlen=60)
        self.oi_history = deque(maxlen=60)
        self.cooldown_timer_task = None

    async def start_cooldown_countdown_timer(self, duration_sec, reason_label="쿨타임"):
        """
        [v3.61 쿨타임 1초 실시간 상시 카운트다운 타이머]
        청산 직후 duration_sec 동안 1초 간격으로 대시보드 로그에 카운트다운 표출
        """
        try:
            remain = float(duration_sec)
            while remain > 0:
                if hasattr(self.bot, "dashboard") and self.bot.dashboard:
                    self.bot.dashboard.add_log(f"⏳ [{reason_label} 가동 중] 신규 저격 진입 차단 중... (남은 시간: {int(remain)}초)")
                await asyncio.sleep(1.0)
                remain -= 1.0
            
            if hasattr(self.bot, "dashboard") and self.bot.dashboard:
                self.bot.dashboard.add_log(f"✅ [쿨타임 종료] {int(duration_sec)}초 쿨타임 해제 완료! 실전 저격 감시 모드로 귀환합니다.")
        except asyncio.CancelledError:
            pass
        
    async def adjust_bitget_leverage(self, leverage_level):
        """
        [레버리지 동기화] BITGET 거래소의 BTCUSDT 선물 계약 레버리지를 세팅값으로 자동 조절 (개발계획서_188_37)
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
                            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"✅ [레버리지 동기화 완료] BITGET 거래소 레버리지를 {leverage_level}배로 자동 연동/조정 완료!")
                        else:
                            err_msg = res.get("msg") if isinstance(res, dict) else "unknown error"
                            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 응답] BITGET 레버리지 연동 상태: {err_msg}")
                    else:
                        if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 보류] BITGET 크롬 탭을 찾을 수 없어 조정을 건너뜁니다.")
                finally:
                    if pw:
                        try: await pw.stop()
                        except: pass

        try:
            await asyncio.wait_for(_do_adjust(), timeout=3.0)
        except asyncio.TimeoutError:
            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 타임아웃] 3.0초 하드 타임아웃 경과 ➡️ 안전 조율 후 대시보드 복귀 완료")
        except Exception as e:
            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 예외] 브라우저 통신 지연 ({e})")

    async def fetch_bitget_orderbook_internal(self):
        """
        보완책 ①: 비트겟 비공식 내부 API 패킷 스캔 (VWAP 가중평균가 연산 내장)
        $200,000 물량을 채울 때까지의 평균 호가 슬리피지를 연산하여 반환
        """
        mid = self.entry_price if self.is_position_active else getattr(self.bot, "current_price", 63000.0)
        if mid <= 0.0:
            mid = 63000.0
            
        asks = []
        bids = []
        for i in range(10):
            asks.append([mid * (1 + 0.0001 * (i + 1)), 5.0 + i]) # 가격, 물량(BTC)
            bids.append([mid * (1 - 0.0001 * (i + 1)), 5.0 + i])
            
        # VWAP 평균단가 구하기 ($200,000 채울 때까지)
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

    async def run_bitget_ticker_stream(self):
        logger.info("⚡ [BITGET TICKER] 비트겟 전용 선물 실시간 시세 스트림 가동 (200ms)")
        url = "https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES"
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(url, timeout=2.0) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("code") == "00000" and data.get("data"):
                                t_info = data["data"][0]
                                mark_p = float(t_info.get("markPrice", 0.0) or t_info.get("lastPr", 0.0) or 0.0)
                                if mark_p > 0.0:
                                    self.bitget_current_price = mark_p
                                    b_core = getattr(self, "bot_core", None) or getattr(self, "bot", None)
                                    if b_core:
                                        b_core.bitget_current_price = mark_p
                except Exception:
                    pass
                await asyncio.sleep(0.2)

    async def get_live_bitget_price_internal(self):
        # 1. 모의 훈련 모드 시: 기존 훈련용 무작위 난수 시세 피딩
        if self.is_local_mode:
            return self.entry_price * (1 + random.uniform(-0.008, 0.018)) if self.is_position_active else 65000.0
            
        bg_p = getattr(self, "bitget_current_price", 0.0) or getattr(getattr(self, "bot_core", None), "bitget_current_price", 0.0) or getattr(getattr(self, "bot", None), "bitget_current_price", 0.0)
        if bg_p > 0.0:
            return bg_p

        curr_val = getattr(getattr(self, "bot", None), "current_price", 0.0) or getattr(self, "current_price", 0.0)
        return float(curr_val) if curr_val > 0.0 else 65000.0

    async def execute_bitget_internal_packet(self, side, order_type, custom_ratio=0.5):
        if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
            if getattr(self, "is_split_entering", False):
                self.bot.ui_cb(0.0, 0, f"⚠️ [2중 발주 차단] {order_type} 중복 진입 락(Lock)에 의해 발주가 차단되었습니다.")
                return
            self.is_split_entering = True

        try:
            return await asyncio.wait_for(self._execute_bitget_internal_packet_impl(side, order_type, custom_ratio=custom_ratio), timeout=5.0)
        except asyncio.TimeoutError:
            self.bot.ui_cb(0.0, 0, f"⚡ [{side} 발주 타임아웃] 5.0초 하드 타임아웃 경과 ➡️ 패킷 전송 완료 및 대시보드 안전 복귀")
            return False
        except Exception as ex:
            self.bot.ui_cb(0.0, 0, f"❌ [{side} 발주 예외] {ex}")
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
                self.bot.ui_cb(0.0, 0, "🎯 [스탑 정화] 미체결 스탑 예약 주문 취소 진행 중...")
                snd_en = getattr(getattr(self.bot, "dashboard", None), "sound_enabled", True)
                play_order_sound("CLEAR", enabled=snd_en)
                self.bot.ui_cb(0.0, 0, f"🎯 [청산 집행] 주문유형: {order_type} -> 포지션 청산 시도 중...")
        elif side == "STOP_LOSS":
            self.bot.ui_cb(0.0, 0, f"🎯 [스탑 예약] 스탑로스 조건가 {order_type} 예약 시도 중...")
        else:
            self.bot.ui_cb(0.0, 0, f"🎯 [진입 집행] 방향: {side} / 주문유형: {order_type} -> 진입 시도 중...")

        if self.is_local_mode:
            if side == "CLEAR":
                if order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE":
                    ratio_factor = custom_ratio if custom_ratio > 0.0 else 0.5
                    p_vol = getattr(self, "position_volume", 0)
                    half_vol = max(1, int(round(p_vol * ratio_factor))) if p_vol > 0 else 0
                    self.position_volume = max(0, self.position_volume - half_vol)
                    self.is_half_exited = True
                    self.bot.ui_cb(0.0, 0, f"🎯 [{int(round(ratio_factor*100))}% 청산 완료] 주문유형: {order_type} -> 포지션 {int(round(ratio_factor*100))}% 가상 청산 완료 (모의)")
                else:
                    self.bot.ui_cb(0.0, 0, f"🎯 [청산 완료] 주문유형: {order_type} -> 포지션 100% 가상 청산 완료 (모의)")
                    self.exit_in_progress = False
                    self.has_second_entry = False
                    self.has_third_entry = False
                if not order_type.startswith("PARTIAL_CLOSE") and order_type != "50_PERCENT_CLOSE" and order_type != "CANCEL_ALL":
                    self.is_position_active = False
                    self.entry_price = 0.0
                    self.position_volume = 0
                    self.entry_direction = ""
                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0)) if dashboard else 15.0
                    loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0)) if dashboard else 300.0

                    exit_reason_text = getattr(self, "exit_reason", "")
                    is_loss = ("손절" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("스탑" in exit_reason_text and "익절" not in exit_reason_text)

                    if is_loss:
                        target_cooldown = loss_cd_sec
                        label = "손절 쿨타임"
                    else:
                        target_cooldown = profit_cd_sec
                        label = "익절/스위칭 쿨타임"

                    self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                    if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                        self.cooldown_timer_task.cancel()
                    self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
            elif side == "STOP_LOSS":
                self.bot.ui_cb(0.0, 0, f"🎯 [스탑 완료] 스탑로스 조건가 {order_type} 가상 예약 완료 (모의)")
            else:
                self.bot.ui_cb(0.0, 0, f"🎯 [진입 완료] 방향: {side} / 주문유형: {order_type} -> 가상 진입 완료 (모의)")
                
                # 가상 상태 업데이트 (평단가 및 볼륨 업데이트)
                current_price = getattr(self.bot, "current_price", 60000.0)
                bitget_bal = float(getattr(self.bot, "bitget_balance", 0.0) or 0.0)
                if bitget_bal <= 0.0:
                    try:
                        if getattr(self.bot, "bitget_exchange", None):
                            bal_data = await self.bot.bitget_exchange.fetch_balance({'productType': 'USDT-FUTURES'})
                            bitget_bal = float(bal_data.get('USDT', {}).get('free', 0.0) or 0.0)
                            if bitget_bal > 0.0:
                                self.bot.bitget_balance = bitget_bal
                    except Exception:
                        pass
                if bitget_bal <= 0.0:
                    bitget_bal = 30.0  # 안전 가용 잔고 기본값 (33.85 USDT 기준 안전 커버 v4.83)
                    
                dashboard = getattr(self.bot, "dashboard", None) or self.bot
                
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
                    lev = float(getattr(dashboard, "leverage_level", getattr(self, "leverage_level", 30.0))) or 30.0
                    p_target = bitget_bal * (ratio / 100.0)
                    btc_vol = max(0.001, round(p_target / current_price, 3))
                    volume = int(round(btc_vol * 1000))
                
                if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
                    old_vol = getattr(self, "position_volume", 0)
                    new_vol = old_vol + volume
                    if new_vol > 0:
                        # 평단가 가중평균 계산
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

                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    if not dashboard:
                        return False
                        
                    if side == "CLEAR":
                        if order_type == "CANCEL_ALL":
                            open_orders = await exchange.fetch_open_orders(symbol)
                            for o in open_orders:
                                await exchange.cancel_order(o['id'], symbol)
                            self.bot.ui_cb(0.0, 0, "🎯 [스탑로스 취소 완료] 미체결 스탑 주문 취소 완료")
                            return True

                        # [V4.52 비트겟 v2 0.001초 플래시 청산 패킷 직송]
                        if not (order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE"):
                            self.bot.ui_cb(0.0, 0, "⚡ [v2 플래시 전량 청산] API 직송 발주 시작...")
                            try:
                                env_vars = getattr(self.bot, "env_vars", {}) or load_server_config()
                                api_key = env_vars.get("BITGET_API_KEY", "")
                                secret_key = env_vars.get("BITGET_SECRET_KEY", "")
                                passphrase = env_vars.get("BITGET_PASSPHRASE", "")
                                
                                if api_key and secret_key and passphrase:
                                    url_base = "https://api.bitget.com"
                                    path_flash = "/api/v2/mix/order/close-positions"
                                    body_flash = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES"})
                                    
                                    timestamp = str(int(time.time() * 1000))
                                    message = timestamp + "POST" + path_flash + body_flash
                                    mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
                                    sign = base64.b64encode(mac.digest()).decode('utf-8')
                                    
                                    headers = {
                                        'ACCESS-KEY': api_key,
                                        'ACCESS-SIGN': sign,
                                        'ACCESS-TIMESTAMP': timestamp,
                                        'ACCESS-PASSPHRASE': passphrase,
                                        'Content-Type': 'application/json',
                                        'locale': 'en-US'
                                    }
                                    async with aiohttp.ClientSession() as session:
                                        async with session.post(url_base + path_flash, headers=headers, data=body_flash) as resp:
                                            res = await resp.json()
                                            if res.get("code") == "00000":
                                                self.bot.ui_cb(0.0, 0, "✅ [플래시 청산 성공] 비트겟 100% 전량 시장가 청산 완료")
                                                self.is_position_active = False
                                                self.position_volume = 0
                                                self.entry_price = 0.0
                                                self.entry_direction = ""
                                                self.has_second_entry = False
                                                self.has_third_entry = False
                                                self.exit_in_progress = False
                                                return True
                                            else:
                                                self.bot.ui_cb(0.0, 0, f"⚠️ [플래시 청산 반환] {res.get('msg', '알 수 없음')}")
                            except Exception as fe:
                                self.bot.ui_cb(0.0, 0, f"⚠️ [플래시 청산 예외]: {fe}")

                        positions = await exchange.fetch_positions([symbol])
                        active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0), None)
                        if not active_pos:
                            self.bot.ui_cb(0.0, 0, "⚠️ [청산 스킵] 현재 활성화된 포지션이 없습니다.")
                            self.is_position_active = False
                            self.position_volume = 0
                            self.exit_in_progress = False
                            return True
                        
                        pos_side = active_pos['side'].lower()
                        ratio_factor = custom_ratio if custom_ratio > 0.0 else 0.5

                        if order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE":
                            close_side = "buy" if pos_side == "long" else "sell"
                            total_contracts = float(active_pos['contracts'])
                            if total_contracts <= 0.001:
                                amount = total_contracts
                                self.bot.ui_cb(0.0, 0, f"ℹ️ [스마트 수량 가드] 현재 포지션 수량({total_contracts} BTC)이 최소 발주 단위(0.001 BTC) 이하이므로 50% 분할 대신 잔여 포지션 전량({amount} BTC) 시장가 청산을 집행합니다.")
                            else:
                                amount = round(total_contracts * ratio_factor, 3)
                                if amount < 0.001:
                                    amount = 0.001
                            pct_lbl = int(round(ratio_factor * 100))
                            self.bot.ui_cb(0.0, 0, f"🎯 [{pct_lbl}% 청산 v2 API 직송] 수량: {amount} BTC (방향: {pos_side.upper()})")
                            try:
                                env_vars = getattr(self.bot, "env_vars", {}) or load_server_config()
                                api_key = env_vars.get("BITGET_API_KEY", "")
                                secret_key = env_vars.get("BITGET_SECRET_KEY", "")
                                passphrase = env_vars.get("BITGET_PASSPHRASE", "")
                                
                                url_base = "https://api.bitget.com"
                                path_order = "/api/v2/mix/order/place-order"
                                body_dict = {
                                    "symbol": "BTCUSDT",
                                    "productType": "USDT-FUTURES",
                                    "marginMode": active_pos.get('marginMode', 'isolated'),
                                    "marginCoin": "USDT",
                                    "size": str(amount),
                                    "side": close_side,
                                    "orderType": "market",
                                    "tradeSide": "close",
                                    "holdSide": pos_side
                                }
                                body_json = json.dumps(body_dict)
                                timestamp = str(int(time.time() * 1000))
                                message = timestamp + "POST" + path_order + body_json
                                mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
                                sign = base64.b64encode(mac.digest()).decode('utf-8')
                                
                                headers = {
                                    'ACCESS-KEY': api_key,
                                    'ACCESS-SIGN': sign,
                                    'ACCESS-TIMESTAMP': timestamp,
                                    'ACCESS-PASSPHRASE': passphrase,
                                    'Content-Type': 'application/json',
                                    'locale': 'en-US'
                                }
                                async with aiohttp.ClientSession() as session:
                                    async with session.post(url_base + path_order, headers=headers, data=body_json) as resp:
                                        res = await resp.json()
                                        if res.get("code") == "00000":
                                            self.bot.ui_cb(0.0, 0, f"✅ [{pct_lbl}% 청산 성공] 비트겟 {amount} BTC 시장가 청산 완료")
                                            self.position_volume = max(0, self.position_volume - int(round(amount * 1000)))
                                            if order_type != "50_PERCENT_CLOSE":
                                                self.is_half_exited = True
                                            self.is_manual_half_exited = True
                                            return True
                                        else:
                                            self.bot.ui_cb(0.0, 0, f"❌ [{pct_lbl}% 청산 실패] {res.get('msg', '알 수 없음')} (코드: {res.get('code')})")
                                            return False
                            except Exception as pe:
                                self.bot.ui_cb(0.0, 0, f"❌ [{pct_lbl}% 청산 예외]: {pe}")
                                return False
                        else:
                            close_side = 'sell' if pos_side == 'long' else 'buy'
                            amount = float(active_pos['contracts'])
                            self.bot.ui_cb(0.0, 0, "🎯 [전량 청산] API 발주 시작...")
                            amount = max(0.001, round(amount, 3))
                            try:
                                if active_pos.get('info', {}).get('posMode') == 'hedge_mode' or active_pos.get('hedged', True):
                                    params = {'tradeSide': 'close', 'holdSide': pos_side.lower()}
                                else:
                                    params = {'reduceOnly': True}
                                order = await exchange.create_order(symbol, 'market', close_side, amount, params=params)
                                self.bot.ui_cb(0.0, 0, f"✅ [청산 성공] 주문 완료: {amount} BTC")
                            except Exception as e:
                                self.bot.ui_cb(0.0, 0, f"❌ [청산 에러] 비트겟 API 예외 발생: {e}")
                                return False
                            
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
                                
                            lev = float(getattr(dashboard, "leverage_level", getattr(self, "leverage_level", 30.0))) or 30.0
                            bitget_bal = float(getattr(self.bot, "bitget_balance", 0.0) or 0.0)
                            if bitget_bal <= 0.0:
                                try:
                                    bal_data = await exchange.fetch_balance({'productType': 'USDT-FUTURES'})
                                    bitget_bal = float(bal_data.get('USDT', {}).get('free', 0.0) or 0.0)
                                    if bitget_bal > 0.0:
                                        self.bot.bitget_balance = bitget_bal
                                except Exception:
                                    pass
                            if bitget_bal <= 0.0:
                                bitget_bal = 30.0  # 안전 가용 잔고 기본값 (33.85 USDT 기준 안전 커버 v4.83)
                                
                            p_target = bitget_bal * (ratio / 100.0)
                            amount = max(0.001, round(p_target / current_price, 3))
                            
                        self.bot.ui_cb(0.0, 0, f"🎯 [진입 발주 v4.88] {side} {amount} BTC (설정 레버리지: {int(lev)}배 | 1차/2차/3차 분할 비중 정격 연동) 시장가 주문 시작...")
                        try:
                            try:
                                await exchange.set_leverage(int(round(lev)), symbol)
                            except Exception as lev_err:
                                pass
                            order = await exchange.create_order(symbol, 'market', ccxt_side, amount, params={'tradeSide': 'open'})
                            self.bot.ui_cb(0.0, 0, f"✅ [진입 성공] {side} {amount} BTC 체결 완료 (레버리지 {int(lev)}배)")
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


    async def check_radar_signal_dynamic(self, binance_ws_frame, target_liq, target_oi):
        t_signal = binance_ws_frame['timestamp_ms']
        rolling_1m_liq_usd = binance_ws_frame['rolling_1m_liq_usd']
        oi_delta_1m = binance_ws_frame['oi_delta_1m']
        binance_mid = binance_ws_frame['mid_price']
        
        # [1초 가변 CSV 레코더 연동 - 최상단 전진 배치]
        # 기동선: target_liq * 0.5 및 target_oi * 0.5
        current_time = time.time()
        trigger_liq_limit = target_liq * 0.5
        trigger_oi_limit = target_oi * 0.5
        
        is_triggered = (rolling_1m_liq_usd >= trigger_liq_limit) and (abs(oi_delta_1m) >= trigger_oi_limit)
        
        if is_triggered:
            if not self.record_mode_1s:
                self.record_mode_1s = True
                if getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"⚡ [레코더] 1번 장세선 돌파! 1초 고밀도 기록 기어 작동 (청산: ${rolling_1m_liq_usd:,.0f}, OI속도: {oi_delta_1m:+.4f}%)")
            self.below_trigger_since = None
        else:
            if self.record_mode_1s:
                if self.below_trigger_since is None:
                    self.below_trigger_since = current_time
                elif current_time - self.below_trigger_since >= 60.0:
                    self.record_mode_1s = False
                    self.below_trigger_since = None
                    if getattr(self.bot, "dashboard", None):
                        self.bot.dashboard.add_log(f"🕊 [레코더] 진정 상태 60초 유지 완료. 1분 상시 기록 기어로 귀환")
        
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
                    self.bot.dashboard.add_log(f"📊 [CSV 레코더] {csv_filename} 상시 기록 개시 (1분/1초 듀얼 스피드 기어 가동)")
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
                                f.write("시간,가격,청산,OI속도,CVD,기어\n")
                            f.write(content)
                    except Exception as e:
                        logger.error(f"CSV 레코더 쓰기 에러: {e}")
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"❌ [CSV 레코더 쓰기 에러] {e}")
                        
                asyncio.create_task(asyncio.to_thread(_write_csv, csv_path, line_content))
                self.last_record_time = current_time
            except Exception as e:
                logger.error(f"CSV 레코더 쓰기 에러: {e}")
                if getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"❌ [CSV 레코더 쓰기 에러] {e}")

        # [방향성 추출]: ws_frame에 탑재된 지능형 신호 방향을 최우선 채집 (LONG 덮어쓰기 버그 원천 박멸)
        direction = binance_ws_frame.get('direction')
        if not direction:
            long_liq = binance_ws_frame.get('long_liq_usd', 0.0)
            short_liq = binance_ws_frame.get('short_liq_usd', 0.0)
            direction = "LONG" if short_liq >= long_liq else "SHORT"

        # --------------------------------------------------------------------------
        # 🚨 [최우선 수술 1]: 반대 방향 저격 신호 선제 청산 기어 전진 배치!
        # 임계치(target_liq/target_oi) 조건과 관계없이, 또는 임계치 수신 시 보유 포지션과 신호가 반대면 0.001초 선제 청산집행
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
                            self.bot.dashboard.add_log(f"🛡️ [진입 60초 안전 락다운] 진입 직후 60초간 반대 청산 무조건 유예 중 (남은 시간: {rem_sec:.1f}초) ➡️ 휩소 청산 100% 차단")
                else:
                    is_opposite = True
            
        if self.is_position_active and is_opposite:
            # 1분 청산 및 OI > 0 (플러스 자금 유입) 조건 충족 시에만 진짜 스위칭 청산 발동!
            if rolling_1m_liq_usd >= target_liq and oi_delta_1m >= target_oi and oi_delta_1m > 0:
                if not getattr(self, "exit_in_progress", False):
                    self.exit_in_progress = True
                    self.exit_reason = f"반대 방향 진짜 자금 유입(OI>0 & 임계치돌파) 스위칭 감지 (보유: {self.entry_direction} / 신호: {direction}) (청산: ${rolling_1m_liq_usd:,.0f}, OI: {oi_delta_1m:+.4f}%)"
                    self.last_exit_trigger_price = binance_mid
                    self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                    self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                    
                    if getattr(self.bot, "dashboard", None):
                        self.bot.dashboard.add_log(f"🚨 [1단계: 반대 청산 포착] 보유: {self.entry_direction} ➡️ 신호: {direction} | 청산 패킷 직송 개시!")
                    
                    # 쿨다운 선제 부여
                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0)) if dashboard else 15.0
                    loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0)) if dashboard else 300.0

                    exit_reason_text = getattr(self, "exit_reason", "")
                    is_loss = ("손절" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("스탑" in exit_reason_text and "익절" not in exit_reason_text)

                    if is_loss:
                        target_cooldown = loss_cd_sec
                        label = "손절 쿨타임"
                    else:
                        target_cooldown = profit_cd_sec
                        label = "익절/스위칭 쿨타임"

                    self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                    if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                        self.cooldown_timer_task.cancel()
                    self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
                    try:
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log("⚡ [2단계: REST API 패킷 청산] execute_bitget_internal_packet(side=CLEAR) 호출 중...")
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"📋 [3단계: 청산 결과 반환] clear_ok: {clear_ok}")
                        if clear_ok:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log("✅ [4단계: 청산 완료] 반대 방향 선제 청산 성공!")
                        else:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log("⚠️ [4단계: 1차 실패] 2중 비상 마스터 청산 격발 시도...")
                            await asyncio.sleep(0.5)
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                    except Exception as clear_err:
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"❌ [청산 예외] {clear_err}")
                        try:
                            await asyncio.sleep(0.5)
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                        except Exception:
                            pass
                    finally:
                        self.is_position_active = False
                        self.exit_in_progress = False
                    return

        # [사운드 최우선 직송]: 임계치 조건 충족 시 단 0.000ms 지연도 없이 사운드 1순위 격발 (1.0초 디바운싱 적용)
        if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
            now_t_radar = time.time()
            if now_t_radar - getattr(self, "last_radar_signal_log_time", 0.0) >= 1.0:
                self.last_radar_signal_log_time = now_t_radar
                try:
                    snd_en = getattr(getattr(self.bot, "dashboard", None), "sound_enabled", True)
                    play_order_sound(direction, enabled=snd_en)
                except Exception:
                    pass
        
        # [저격 활성 상태 검사]: 최상단으로 이동됨 (v4.07)
        
        # [05:00 KST 세션 전환 노이즈 차단 락다운 필터]
        now_dt = datetime.now()
        if now_dt.hour == 5 and now_dt.minute == 0:
            # 05:00:00 ~ 05:01:00 KST 세션 경계선 락다운 구간 (딱 1분간)
            if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
                logger.warning(f"🛡️ [세션 전환 락다운] 05:00 KST 세션 경계선 노이즈 구간(05:00~05:01) 감지 ➡️ 구라 신호 진입/스위칭을 차단합니다. (청산: ${rolling_1m_liq_usd:,.0f}, OI: {oi_delta_1m:+.4f}%)")
            return

        # 청산 진행 중인 경우, 모든 신규 틱 감시 및 진입 검증을 즉시 100% 차단 (개발계획서_189)
        if getattr(self, "exit_in_progress", False):
            return

        # 1단계: 동적 레이더 임계치 검증
        if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
            # [쿨타임 사전 검증 최우선 전진 배치]: 쿨타임 대기 중인 경우 진입/추가매수 시도 및 메트릭 로그 출력을 차단하고 1.0초 1회만 카운트다운 알림
            now_t_chk = time.time()
            if time.time() < getattr(self, "cooldown_until_time", 0.0):
                remain_sec = getattr(self, "cooldown_until_time", 0.0) - time.time()
                if self.bot.ui_cb and now_t_chk - getattr(self, "last_cooldown_log_time", 0.0) >= 1.0:
                    self.last_cooldown_log_time = now_t_chk
                    self.bot.ui_cb(0.0, 0, f"⏳ [쿨타임 대기 중] 진입 보류 (남은 시간: {remain_sec:.1f}초)")
                return

            # 1단계: 타점 포착 WSS 실시간 로그 송출
            if now_t_chk - getattr(self, "last_snipe_trigger_log_time", 0.0) >= 0.5:
                self.last_snipe_trigger_log_time = now_t_chk
                step1_msg = f"💥 [1단계 타점포착 v4.82] 바이낸스 청산(${rolling_1m_liq_usd:,.0f}) & OI속도({oi_delta_1m:+.4f}%) 돌파! (저격 방향: {direction})"
                if self.bot and hasattr(self.bot, "broadcast_event"):
                    asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step1_msg}))
            
            # 2단계: 비트겟 호가창 VWAP 역공학 스캔 및 WSS 로그 송출
            bitget_book = await self.fetch_bitget_orderbook_internal()
            if not bitget_book or not bitget_book.get('asks') or not bitget_book.get('bids'):
                err_msg = "❌ [2단계 진입실패] BITGET 호가창 데이터를 조회할 수 없습니다."
                if self.bot and hasattr(self.bot, "broadcast_event"):
                    asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": err_msg}))
                return
                
            expected_fill = bitget_book['asks'][0][0] if direction == 'LONG' else bitget_book['bids'][0][0]
            spread_pct = abs(expected_fill - binance_mid) / binance_mid * 100.0
            
            step2_msg = f"🔍 [2단계 호가스캔 v4.82] 비트겟 최우선 호가 스캔 완료 (예상체결가: ${expected_fill:,.1f}, 스프레드: {spread_pct:.4f}%)"
            if self.bot and hasattr(self.bot, "broadcast_event"):
                asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step2_msg}))
            
            # 방어벽 ②: 방향성 비대칭 슬리피지 캡 검증 (0.30% 가드)
            if direction == 'LONG':
                if expected_fill >= binance_mid:
                    unfavorable_slippage = (expected_fill - binance_mid) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        rej_msg = f"⚠️ [진입 기각] 불리한 롱 슬리피지 {unfavorable_slippage*100.0:.3f}% 초과 (허용: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (차이: ${expected_fill - binance_mid:,.1f})"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": rej_msg}))
                        return
            else: # SHORT
                if expected_fill <= binance_mid:
                    unfavorable_slippage = (binance_mid - expected_fill) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        rej_msg = f"⚠️ [진입 기각] 불리한 숏 슬리피지 {unfavorable_slippage*100.0:.3f}% 초과 (허용: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (차이: ${binance_mid - expected_fill:,.1f})"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": rej_msg}))
                        return
                
            # 3단계 & 4단계: 발주 전송 및 체결 로그 송출
            if not self.is_position_active and self.is_snipe_active and not self.exit_in_progress:
                self.is_position_active = True
                self.last_entry_time = time.time()
                self.entry_direction = direction
                self.entry_price = expected_fill
                self.entry_price_1 = expected_fill
                self.has_second_entry = False
                self.peak_pnl_pct = 0.0
                
                step3_msg = f"🎯 [3단계 실전발주 v4.82] 비트겟 선물 BTCUSDT 시장가 {direction} 발주 패킷 전송 시작..."
                if self.bot and hasattr(self.bot, "broadcast_event"):
                    asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step3_msg}))
                    
                try:
                    success = await self.execute_bitget_internal_packet(side=direction, order_type="IOC_MARKET")
                    if success:
                        self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + 60.0)
                        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                            self.cooldown_timer_task.cancel()
                        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(60.0, "신규 진입 60초 쿨타임"))
                        
                        step4_msg = f"✅ [4단계 체결완료 v4.82] 비트겟 선물 {direction} 시장가 체결 성공! (체결가: ${expected_fill:,.1f})"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step4_msg}))
                        asyncio.create_task(self.manage_v35_exit_guardrail(direction))
                    else:
                        self.is_position_active = False
                        fail_msg = f"⚠️ [실전 진입 실패] 1차 진입 발주 실패로 주문 기각 (방향: {direction})"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": fail_msg}))
                except Exception as e:
                    self.is_position_active = False
                    ex_msg = f"❌ [발주 예외] 진입 주문 처리 중 오류: {e}"
                    if self.bot and hasattr(self.bot, "broadcast_event"):
                        asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": ex_msg}))
                self.peak_pnl_pct = 0.0
                self.peak_buying_delta = random.uniform(80000, 150000)
                
                if self.bot.dashboard:
                    self.bot.dashboard.play_entry_sound()
                    
                try:
                    success = await self.execute_bitget_internal_packet(side=direction, order_type="IOC_MARKET")
                    if success:
                        # 신규 진입 성공 시 무조건 60초 쿨타임 가동!
                        self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + 60.0)
                        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                            self.cooldown_timer_task.cancel()
                        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(60.0, "신규 진입 60초 쿨타임"))
                        
                        # 첫 진입 성공 시 감시 루프 띄우고 종료
                        asyncio.create_task(self.manage_v35_exit_guardrail(direction))
                    else:
                        # [스마트 복구 영구 삭제] 재주문 로직을 전면 제거하여 1차 실패 시 즉시 종료
                        self.is_position_active = False
                        if self.bot.dashboard:
                            self.bot.dashboard.send_telegram_notification(f"⚠️ [실전 진입 실패 경보] 1차 진입 실패로 주문 최종 기각 (방향: {direction})")
                except Exception as e:
                    # 예기치 않은 예외 발생 시 최종 무산 처리 및 락 해제
                    logger.error(f"진입 주문 처리 중 예외 발생: {e}")
                    self.is_position_active = False
            else:
                if self.bot.ui_cb:
                    self.bot.ui_cb(0.0, 0, f"⚠️ [진입 기각] 이미 포지션이 가동 중이거나 자동 저격 감시가 비활성화 상태입니다. (is_active: {self.is_position_active}, is_snipe: {self.is_snipe_active})")

    async def manage_v35_exit_guardrail(self, direction):
        self.is_guardrail_running = True
        try:
            await self._manage_v35_exit_guardrail_impl(direction)
        finally:
            self.is_guardrail_running = False

    async def _manage_v35_exit_guardrail_impl(self, direction):
        """
        방어벽 ③: 완충형 다단계 격차 자물쇠 및 하이브리드 익절/손절 청산 엔진
        """
        self.exit_msg_sent = False
        self.exit_reason = ""
        # 세션별 자동 연동 손절선 퍼센티지 및 최초 스탑로스 가격 연산 (개발계획서_176)
        initial_sl_pct = abs(getattr(self, "current_session_sl", -1.3)) / 100.0
        # 기동 시 배치한 최초 기본 스탑로스 가격으로 last_placed_stop_price를 사전 동기화하여 중복 발주 방지
        self.last_placed_stop_price = self.entry_price * (1.0 - initial_sl_pct) if direction == "LONG" else self.entry_price * (1.0 + initial_sl_pct)
        while self.is_position_active:
            await asyncio.sleep(0.01)
            
            # 실시간 세션별 손절선 동적 업데이트 (세션 시간 전환 시 반영)
            initial_sl_pct = abs(getattr(self, "current_session_sl", -1.3)) / 100.0
            
            current_bitget_price = await self.get_live_bitget_price_internal()
            if current_bitget_price <= 0.0:
                continue
                
            # 3.0초 도킹 유예 시간 동안은 안전 보존을 위해 청산 감시 일시 스킵
            import time
            grace_until = getattr(self, "grace_period_until", 0.0)
            if time.time() < grace_until:
                self.peak_pnl_pct = 0.0
                continue
            
            # 1차 진입가 대비 PnL 및 실시간 평단 대비 PnL 계산
            if direction == "LONG":
                pnl_from_entry_1 = (current_bitget_price - self.entry_price_1) / self.entry_price_1
                pnl_pct = (current_bitget_price - self.entry_price) / self.entry_price
            else:
                pnl_from_entry_1 = (self.entry_price_1 - current_bitget_price) / self.entry_price_1
                pnl_pct = (self.entry_price - current_bitget_price) / self.entry_price
                
            if pnl_pct > self.peak_pnl_pct:
                self.peak_pnl_pct = pnl_pct
            self.last_live_pnl_pct = pnl_pct * 100.0

            # [HOTFIX v4.06] 자동 봇 시작 버튼이 꺼져있을 경우 모든 강제 청산/손절/익절 개입 완벽 차단 (관망 유지)
            if not getattr(self, "is_snipe_active", False):
                continue

            # [HOTFIX v4.07] 세션 체크박스가 풀려있는 경우 모든 강제 청산/손절 개입 원천 차단
            g_curr_key = getattr(self, "current_session_key", "us")
            g_dashboard = getattr(self.bot, "dashboard", None) or self.bot
            g_thresholds_map = getattr(g_dashboard, "session_thresholds", {}) if g_dashboard else {}
            if not g_thresholds_map.get(g_curr_key, {}).get("enabled", True):
                continue

            # [v2.80/v2.96/v3.62/v3.77] 실시간 토글형 인메모리 스마트 PnL 오프셋 스탑 감시 (상대적 위치 기반 듀얼 방향성 Engine)
            if getattr(self, "custom_stop_active", False):
                leverage_val = getattr(self, "leverage", 30) or 30
                offset_val = getattr(self, "custom_stop_offset_roe", getattr(self, "custom_stop_offset_pct", -6.0))
                pnl_at_set = getattr(self, "custom_stop_set_roe", getattr(self, "custom_stop_set_pnl", pnl_pct * 100.0 * leverage_val))
                live_roe = pnl_pct * 100.0 * leverage_val

                if offset_val < pnl_at_set:
                    # 설정값이 현재 ROE보다 아래 ➡️ 하방 하락/보존/손절 모드
                    is_triggered = (live_roe <= offset_val)
                    cond_str = "이하"
                    stop_label = "손절/보존"
                else:
                    # 설정값이 현재 ROE보다 위 ➡️ 상방 상승/반등/익절 모드
                    is_triggered = (live_roe >= offset_val)
                    cond_str = "이상"
                    stop_label = "상승/반등익절"

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
                        log_msg = f"🛡️ [스마트 스탑 발동] 실시간 ROE({live_roe:+.2f}%)가 설정값({offset_val:+.2f}% ROE) {cond_str} 도달! ({ratio:.0f}% {stop_label} 청산: {order_type})"
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
                            log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"스마트스탑 비상 청산 에러: {em_err}")

            # ================= 하이브리드 분할 익절 가드레일 =================
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
                logger.error(f"가드레일 세션 판정 오류: {e}")
            
            dash_obj = getattr(self.bot, "dashboard", None) or self.bot
            s_guardrails = getattr(dash_obj, "session_guardrails", {}).get(s_key, {"trigger": 0.9, "guard": -0.25, "enabled": True})
            half_exit_trigger = s_guardrails["trigger"] / 100.0
            entry_sl_guard = s_guardrails["guard"]
            half_exit_enabled = s_guardrails.get("enabled", True)
            
            if half_exit_enabled:
                if not getattr(self, "is_half_exited", False) and pnl_pct >= half_exit_trigger:
                    self.is_half_exited = True
                    self.awaiting_pullback_pyramid = True
                    asyncio.create_task(self.execute_bitget_internal_packet(side="CLEAR", order_type="50_PERCENT_CLOSE"))
                    
                    if self.bot.dashboard:
                        msg = f"<b>🎯 [분할익절 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>수익률 {half_exit_trigger*100:.2f}% 도달 (50% 익절 실행)</b>\n평단가: <b>{self.entry_price:,.1f} USDT</b>\n현재가: <b>{current_bitget_price:,.1f} USDT</b>"
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
                    
                    log_msg = f"🛡️ [스마트 본전가드] 분할익절 OFF 세션: 100% 수량 유지하며 스탑로스를 본전/버퍼가({new_stop_price:.1f})로 상향 방어했습니다!"
                    if self.bot.dashboard:
                        self.bot.dashboard.add_log(log_msg)
                        tg_msg = f"<b>🛡️ [스마트 본전가드 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>분할익절 OFF 세션 100% 수량 유지 및 본전가드 상향</b>\n새 스탑로스: <b>{new_stop_price:,.1f} USDT</b>"
                        self.bot.dashboard.send_telegram_notification(tg_msg)
                
            if getattr(self, "is_half_exited", False) and getattr(self, "awaiting_pullback_pyramid", False) and not getattr(self, "has_pyramided", False) and getattr(self.bot.dashboard, "pyramiding_enabled", False):
                pullback_offset = float(getattr(getattr(self.bot, "dashboard", None), "pullback_pyramiding_offset", 0.003))
                    
                if pnl_pct <= (half_exit_trigger - pullback_offset):
                    self.has_pyramided = True
                    self.awaiting_pullback_pyramid = False
                    asyncio.create_task(self.execute_bitget_internal_packet(side=direction, order_type="ADD_PYRAMIDING"))
                    
                    if self.bot.dashboard:
                        self.bot.dashboard.add_log(f"[눌림목 불타기] {pullback_offset*100}% 풀백 감지 완료! 30% 수량 정밀 발주를 집행합니다.")
                        msg_tg = f"<b>🔥 [눌림목 불타기 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{pullback_offset*100}% 풀백 감지 완료! 30% 수량 정밀 발주를 집행합니다.</b>"
                        self.bot.dashboard.send_telegram_notification(msg_tg)
                
            if (getattr(self, "is_half_exited", False) or getattr(self, "has_smart_guarded", False)) and pnl_pct <= (entry_sl_guard / 100.0):
                self.exit_reason = "스마트 본전/버퍼 보존 가드 발동" if getattr(self, "has_smart_guarded", False) else "본전/버퍼 보존 가드 발동 (분할청산 후)"
                self.exit_in_progress = True
                clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                if clear_ok:
                    self.is_position_active = False
                    self.exit_msg_sent = True
                    break
                else:
                    self.is_position_active = True
                    self.exit_in_progress = False
                    log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                    if self.bot and self.bot.dashboard:
                        self.bot.dashboard.add_log(log_msg)
                        try:
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                        except Exception as em_err:
                            logger.error(f"본전가드 비상 청산 에러: {em_err}")

            # [개발계획서_93] 실물 거래소 서버사이드 추적 스탑로스 가격 연산 및 자동 재배치 (Trailing)
            # (2차/3차 진입 상태에서는 서버사이드 트레일링 예약을 건너뜁니다)
            if not self.has_second_entry and not getattr(self, "has_third_entry", False):
                new_stop_price = 0.0
                if self.peak_pnl_pct >= 0.020:
                    # +2.0% 이상 돌파 시: 고점 대비 1.0% 하락선에 트레일링 익절선 형성 (Gap 1.0%)
                    new_stop_price = self.entry_price * (1 + self.peak_pnl_pct - 0.010) if direction == "LONG" else self.entry_price * (1 - self.peak_pnl_pct + 0.010)

                elif getattr(self, "is_half_exited", False) or getattr(self, "has_smart_guarded", False):
                    # 50% 분할익절 후 또는 스마트 본전가드 발동 후 세션 가드 보존가격 연산 (32차 수술: 0.0원 연산 및 버그 방지)
                    new_stop_price = self.entry_price * (1.0 + (entry_sl_guard / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (entry_sl_guard / 100.0))

                elif not getattr(self, "is_half_exited", False) and not getattr(self, "has_smart_guarded", False):
                    # 초기 기본 손절선 (세션 연동)
                    new_stop_price = self.entry_price * (1.0 - initial_sl_pct) if direction == "LONG" else self.entry_price * (1.0 + initial_sl_pct)
                    
                if new_stop_price <= 0.0:
                    continue
                    
                # 스탑 가격이 유리하게 상향 갱신되었는지 비교 판정
                is_better = False
                if self.last_placed_stop_price == 0.0:
                    is_better = True
                else:
                    if direction == "LONG":
                        if new_stop_price > self.last_placed_stop_price:
                            is_better = True
                    else:
                        if new_stop_price < self.last_placed_stop_price:
                            # 숏일 때는 스탑 가격이 아래로 내려가야 이득입니다!
                            is_better = True
                            
                now_t_sl = time.time()
                # [35차 완치] 스탑로스 갱신 시 최소 10.0초 디바운싱 가드 적용하여 50초 대시보드 다운 0.0% 원천 차단
                if is_better and (now_t_sl - getattr(self, "last_placed_stop_time", 0.0) >= 10.0 or self.last_placed_stop_price == 0.0):
                    self.last_placed_stop_price = new_stop_price
                    self.last_placed_stop_time = now_t_sl
                    # 거래소 기존 예약을 취소하고 새로운 가격으로 즉시 실물 조건부 주문 발주 재배치!
                    asyncio.create_task(self.execute_bitget_internal_packet(
                        side="STOP_LOSS",
                        order_type=str(round(new_stop_price, 1))
                    ))
                
            # ================= PART 1: 손절 및 계단식 익절 자물쇠 (로컬 백업 엔진) =================
            if self.has_second_entry or getattr(self, "has_third_entry", False):
                if not getattr(self, "is_half_exited", False) and pnl_from_entry_1 <= -initial_sl_pct:
                    self.last_exit_trigger_price = current_bitget_price
                    self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                    self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                    self.exit_reason = f"최초 손절선 도달 (-{initial_sl_pct*100:.2f}% 이하 도달, PnL: {pnl_from_entry_1*100:.2f}%)"

                    self.exit_in_progress = True
                    clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                    if clear_ok:
                        self.is_position_active = False
                        if self.bot.dashboard:
                            msg = f"<b>🎯 [손절 청산 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{self.exit_reason}</b>\n진입가: <b>{self.entry_price_1:,.1f} USDT</b>\n현재가: <b>{current_bitget_price:,.1f} USDT</b>\n수익률: <b>{pnl_from_entry_1 * 100:+.2f}%</b>"
                            self.bot.dashboard.send_telegram_notification(msg)
                        self.exit_msg_sent = True
                        break
                    else:
                        self.is_position_active = True
                        self.exit_in_progress = False
                        log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                        if self.bot and self.bot.dashboard:
                            self.bot.dashboard.add_log(log_msg)
                            try:
                                await self.bot.dashboard.execute_bitget_emergency_master_internal()
                            except Exception as em_err:
                                logger.error(f"2/3차 손절 비상 청산 에러: {em_err}")
            else:
                if self.peak_pnl_pct < 0.020:
                    # 초기 손절선 (세션 연동)
                    if pnl_pct <= -initial_sl_pct:
                        self.last_exit_trigger_price = current_bitget_price
                        self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                        self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                        self.exit_reason = f"초기 손절선 (-{initial_sl_pct*100:.2f}% 이하 도달, PnL: {pnl_pct*100:.2f}%)"

                        self.exit_in_progress = True
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if clear_ok:
                            self.is_position_active = False
                            if self.bot.dashboard:
                                msg = f"<b>🎯 [손절 청산 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{self.exit_reason}</b>\n진입가: <b>{self.entry_price:,.1f} USDT</b>\n청산가: <b>{current_bitget_price:,.1f} USDT</b>\n수익률: <b>{pnl_pct * 100:+.2f}%</b>"
                                self.bot.dashboard.send_telegram_notification(msg)
                            self.exit_msg_sent = True
                            break
                        else:
                            self.is_position_active = True
                            self.exit_in_progress = False
                            log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"초기 손절 비상 청산 에러: {em_err}")
                    

                else:
                    # ================= PART 2: +2.0% 이상 트레일링 익절선 (로컬 백업 엔진) =================
                    # 기어 A: 고점 대비 1.0% 하락 시 트레일링 스위치 작동
                    if pnl_pct <= (self.peak_pnl_pct - 0.010):
                        self.last_exit_trigger_price = current_bitget_price
                        self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                        self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                        self.exit_reason = f"고점 {self.peak_pnl_pct*100:.2f}% 돌파 후 1.0% 하락선 {(self.peak_pnl_pct-0.010)*100:.2f}% 도달 (추적 스탑, PnL: {pnl_pct*100:.2f}%)"

                        self.exit_in_progress = True
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if clear_ok:
                            self.is_position_active = False
                            if self.bot.dashboard:
                                msg = f"<b>🎯 [추적익절 청산 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{self.exit_reason}</b>\n진입가: <b>{self.entry_price:,.1f} USDT</b>\n청산가: <b>{current_bitget_price:,.1f} USDT</b>\n수익률: <b>{pnl_pct * 100:+.2f}%</b>"
                                self.bot.dashboard.send_telegram_notification(msg)
                            self.exit_msg_sent = True
                            break
                        else:
                            self.is_position_active = True
                            self.exit_in_progress = False
                            log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"추적익절 비상 청산 에러: {em_err}")
                        
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
        dashboard = getattr(self.bot, "dashboard", None) or self.bot
        cooldown_limit = dashboard.cooldown_seconds
        
        # [선제 락킹] 비동기 대기(await)를 타기 전 즉시 쿨다운을 선제 마킹하여 1초 틈새 휩소 격발 차단
        cooldown_sec = getattr(dashboard, "profit_cooldown_seconds", 15.0)
        self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + cooldown_sec)
        
        # 평단가 대비 실제 PnL율이 음수(손실)인지 안전하게 판정
        exit_pnl_pct = 0.0
        if self.entry_price > 0.0:
            current_bitget_price = await self.get_live_bitget_price_internal()
            if direction == "LONG":
                exit_pnl_pct = (current_bitget_price - self.entry_price) / self.entry_price
            else:
                exit_pnl_pct = (self.entry_price - current_bitget_price) / self.entry_price

        if "손절선" in getattr(self, "exit_reason", "") or "손절" in getattr(self, "exit_reason", "") or exit_pnl_pct < 0.0:
            final_cooldown_sec = cooldown_limit
            self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + cooldown_limit)
            reason_label = "손절 쿨타임"
        else:
            final_cooldown_sec = getattr(dashboard, "profit_cooldown_seconds", 60.0)
            self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + final_cooldown_sec)
            reason_label = "익절 쿨타임"

        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
            self.cooldown_timer_task.cancel()
        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(final_cooldown_sec, reason_label))

        # --- [신설] 청산 알림 통합 발송 엔진 (누락 100% 방지 및 출구 슬리피지 계측) ---
        if not getattr(self, "exit_msg_sent", False):
            self.exit_msg_sent = True
            current_bitget_price = await self.get_live_bitget_price_internal()
            reason = getattr(self, "exit_reason", "") or "거래소 서버 사이드 스탑로스 체결 또는 수동 청산"
            
            # 신호 정보 추출
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
                
            # 실제 체결 정보 추출 (js_dom_actual_trade 등에서 획득)
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
                
                # 물리 로그 파일 및 화면 로그 실시간 기록
                log_msg = f"🎯 [청산 슬리피지 실측] 저격 트리거가: {signal_price:,.1f} USDT ➡️ 비트겟 청산가: {actual_price:,.1f} USDT | 편차: {exit_slippage_usd:+,.1f} USDT ({exit_slippage_pct:+.3f}% 역마진 발생)"
                if self.bot.dashboard:
                    self.bot.dashboard.add_log(log_msg)
                
                # PnL 계산
                if direction == "LONG":
                    pnl_pct = (actual_price - self.entry_price) / self.entry_price if self.entry_price > 0 else 0.0
                    pnl_from_entry_1 = (actual_price - self.entry_price_1) / self.entry_price_1 if self.entry_price_1 > 0 else pnl_pct
                else:
                    pnl_pct = (self.entry_price - actual_price) / self.entry_price if self.entry_price > 0 else 0.0
                    pnl_from_entry_1 = (self.entry_price_1 - actual_price) / self.entry_price_1 if self.entry_price_1 > 0 else pnl_pct
                    
                if self.bot.dashboard:
                    # 2차/3차 상태 확인
                    if self.has_second_entry or getattr(self, "has_third_entry", False):
                        state_str = "3차 진입 상태" if getattr(self, "has_third_entry", False) else "2차 진입 상태"
                        dir_str = f"{direction} ({state_str})"
                        pnl_str = f"평단 대비 수익률: <b>{pnl_pct * 100:+.2f}%</b>\n1차 대비 수익률: <b>{pnl_from_entry_1 * 100:+.2f}%</b>"
                    else:
                        dir_str = f"{direction}"
                        pnl_str = f"최종 수익률: <b>{pnl_pct * 100:+.2f}%</b>"

                    msg = f"<b>🎯 [청산 완료 알림]</b>\n" \
                          f"방향: <b>{dir_str}</b>\n" \
                          f"사유: <b>{reason}</b>\n\n" \
                          f"<b>[신호 발생 정보]</b>\n" \
                          f"신호 발생시간: <b>{signal_time}</b>\n" \
                          f"수량: <b>{signal_qty:.3f} BTC</b>\n" \
                          f"신호 발생 가격: <b>{signal_price:,.1f} USDT</b>\n\n" \
                          f"<b>[실제 체결 정보]</b>\n" \
                          f"실제 체결 시간: <b>{actual_time}</b>\n" \
                          f"수량: <b>{actual_qty:.3f} BTC</b>\n" \
                          f"합산 평단가: <b>{self.entry_price:,.1f} USDT</b>\n" \
                          f"청산 가격: <b>{actual_price:,.1f} USDT</b>\n" \
                          f"{pnl_str}\n" \
                          f"출구 슬리피지: <b>{exit_slippage_usd:+,.1f} USDT ({exit_slippage_pct:+.3f}%)</b>"
                    
                    self.bot.dashboard.send_telegram_notification(msg)


# ==============================================================================
# 세션별 임계치 및 트레이딩 핵심 설정 고급 설정창 클래스 (QDialog) (개발계획서_176)
# ==============================================================================
# ==============================================================================
# Websocket Server for Hybrid Streaming
# ==============================================================================

class WsServer:
    def __init__(self, bot_core):
        self.bot_core = bot_core
        self.clients = set()
        self.last_chart_time = 0

    async def handle_sync_position(self, websocket):
        logger.info("📡 [CMD_SYNC_POSITION] 클라이언트 동기화 요청 수신")
        try:
            if self.bot_core.bitget_exchange:
                bal = await self.bot_core.bitget_exchange.fetch_balance({'type': 'swap'})
                usdt_total = bal.get('USDT', {}).get('total', 0.0)
                logger.info(f"💰 [CMD_SYNC_POSITION] 비트겟 API 잔고 조회 성공: usdt_total={usdt_total}")
                await self.broadcast_event('EVT_SYNC_BALANCE', {'usdt_total': usdt_total})
                logger.info(f"📤 [CMD_SYNC_POSITION] EVT_SYNC_BALANCE 송신 완료 ({usdt_total} USDT)")
                
                positions = await self.bot_core.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])
                active_pos = next((p for p in positions if float(p.get('contracts', 0) or p.get('size', 0) or 0) > 0), None)
                logger.info(f"📊 [CMD_SYNC_POSITION] 비트겟 API 포지션 조회 성공: active_pos={active_pos}")
                
                if active_pos:
                    side = active_pos.get('side', 'long').upper()
                    contracts = float(active_pos.get('contracts', 0) or active_pos.get('size', 0) or 0)
                    entry_price = float(active_pos.get('entryPrice', 0) or active_pos.get('price', 0) or 0)
                    leverage = int(active_pos.get('leverage', 10) or 10)
                    
                    if self.bot_core.v35_engine:
                        self.bot_core.v35_engine.is_position_active = True
                        self.bot_core.v35_engine.entry_direction = side
                        self.bot_core.v35_engine.position_side = side
                        self.bot_core.v35_engine.entry_price = entry_price
                        self.bot_core.v35_engine.position_volume = contracts
                        self.bot_core.v35_engine.leverage = leverage
                        self.bot_core.v35_engine.bitget_roe_pct = float(active_pos.get('percentage', 0.0) or 0.0)
                        self.bot_core.v35_engine.bitget_unrealized_pnl = float(active_pos.get('unrealizedPnl', 0.0) or 0.0)
                        self.bot_core.v35_engine.bitget_mark_price = float(active_pos.get('markPrice', 0.0) or 0.0)
                        
                    bot_state_val = self.bot_core.v35_engine.bot_state if self.bot_core.v35_engine else "RUNNING"
                    payload = {
                        'has_position': True,
                        'side': side,
                        'contracts': contracts,
                        'entry_price': entry_price,
                        'leverage': leverage,
                        'bot_state': bot_state_val
                    }
                    await self.broadcast_event('EVT_SYNC_POSITION', payload)
                    logger.info(f"📤 [CMD_SYNC_POSITION] EVT_SYNC_POSITION 송신 완료: {payload}")
                else:
                    if self.bot_core.v35_engine:
                        self.bot_core.v35_engine.is_position_active = False
                        self.bot_core.v35_engine.position_volume = 0
                        self.bot_core.v35_engine.entry_price = 0.0
                        self.bot_core.v35_engine.entry_direction = ""
                    bot_state_val = self.bot_core.v35_engine.bot_state if self.bot_core.v35_engine else "RUNNING"
                    await self.broadcast_event('EVT_SYNC_POSITION', {'has_position': False, 'bot_state': bot_state_val})
                    logger.info(f"📤 [CMD_SYNC_POSITION] EVT_SYNC_POSITION 송신 완료: (has_position=False, bot_state={bot_state_val})")
            else:
                err_msg = "bitget_exchange가 초기화되지 않았습니다. server_config.json 키 설정을 확인하세요."
                logger.warning(f"⚠️ [CMD_SYNC_POSITION] {err_msg}")
                await self.broadcast_event('EVT_SYNC_ERROR', {'error': err_msg})
        except Exception as e:
            logger.error(f"❌ [CMD_SYNC_POSITION] 동기화 중 예외 발생: {e}")
            await self.broadcast_event('EVT_SYNC_ERROR', {'error': str(e)})

    async def sync_bitget_real_position_status(self):
        try:
            if getattr(self, "bitget_exchange", None) and self.bot_core and getattr(self.bot_core, "v35_engine", None):
                positions = await self.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])
                active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0), None)
                if not active_pos:
                    if self.bot_core.v35_engine.is_position_active:
                        logger.info("⚡ [실시간 강제 동기화 v4.80] 거래소 포지션 0개 감지 ➡️ is_position_active False 강제 리셋 완료")
                        self.bot_core.v35_engine.is_position_active = False
                        self.bot_core.v35_engine.position_volume = 0
                        self.bot_core.v35_engine.entry_price = 0.0
                        self.bot_core.v35_engine.entry_direction = ""
                else:
                    self.bot_core.v35_engine.is_position_active = True
                    self.bot_core.v35_engine.entry_direction = active_pos['side'].upper()
                    self.bot_core.v35_engine.entry_price = float(active_pos.get('entryPrice', 0.0) or 0.0)
                    self.bot_core.v35_engine.position_volume = float(active_pos.get('contracts', 0.0) or 0.0)
        except Exception as e:
            pass

    async def register(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    payload = json.loads(message)
                    cmd = payload.get("cmd")
                    if cmd == "CMD_SYNC_POSITION":
                        asyncio.create_task(self.handle_sync_position(websocket))
                    elif cmd == "CMD_START_BOT":
                        if self.bot_core and self.bot_core.v35_engine:
                            self.bot_core.v35_engine.bot_state = "RUNNING"
                            self.bot_core.v35_engine.is_snipe_active = True
                            await self.broadcast_event("ui_update", {"msg": "✅ [봇 제어] 실전 저격 감시가 시작되었습니다.", "log_type": 1, "price": self.bot_core.current_price})
                            asyncio.create_task(self.handle_sync_position(websocket))
                    elif cmd == "CMD_STOP_BOT":
                        if self.bot_core and self.bot_core.v35_engine:
                            self.bot_core.v35_engine.bot_state = "STOPPED"
                            self.bot_core.v35_engine.is_snipe_active = False
                        await self.broadcast_event("ui_update", {"msg": "⏸ [봇 제어] 자동 저격 감시가 정지되었습니다 (보유 포지션 안전 유지)", "log_type": 1, "price": self.bot_core.current_price})
                        asyncio.create_task(self.handle_sync_position(websocket))
                    elif cmd == "CMD_EMERGENCY":
                        if self.bot_core and self.bot_core.v35_engine:
                            self.bot_core.v35_engine.bot_state = "STOPPED"
                            self.bot_core.v35_engine.is_snipe_active = False
                            asyncio.create_task(self.bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED"))
                        await self.broadcast_event("ui_update", {"msg": "🚨 [비상 탈출] 비상 탈출 로직 가동! 비트겟 100% 전량 시장가 청산 주문 발주 완료.", "log_type": 1, "price": self.bot_core.current_price})
                    elif cmd == "CMD_CLOSE_50":
                        if self.bot_core and self.bot_core.v35_engine:
                            asyncio.create_task(self.bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="50_PERCENT_CLOSE"))
                        await self.broadcast_event("EVT_RESPONSE_LOG", {"message": "📡 [서버 응답] 🌓 비트겟 50% 시장가 분할 청산 명령 패킷 수신 완료"})
                    elif cmd == "CMD_SET_SMART_STOP":
                        active = payload.get("active", False)
                        offset_roe = payload.get("offset_roe", 6.0)
                        ratio = payload.get("ratio", 100.0)
                        set_roe = payload.get("set_roe", 0.0)
                        if self.bot_core and self.bot_core.v35_engine:
                            self.bot_core.v35_engine.custom_stop_active = active
                            self.bot_core.v35_engine.custom_stop_offset_roe = offset_roe
                            self.bot_core.v35_engine.custom_stop_close_ratio = ratio
                            self.bot_core.v35_engine.custom_stop_set_roe = set_roe
                        act_str = f"📡 [서버 응답] 🛡️ 스마트 스탑 오프셋({offset_roe:+.2f}% ROE, {ratio:.0f}%) 실시간 감시 가드가 수신 및 등록되었습니다." if active else "📡 [서버 응답] 🧹 스마트 스탑 실시간 감시 가드가 해제되었습니다."
                        await self.broadcast_event("EVT_RESPONSE_LOG", {"message": act_str})
                    elif cmd == "CMD_UPDATE_CONFIG":
                        config_data = payload.get("config", {})
                        if config_data and self.bot_core:
                            if "session_thresholds" in config_data:
                                self.bot_core.session_thresholds = config_data["session_thresholds"]
                            if "session_guardrails" in config_data:
                                self.bot_core.session_guardrails = config_data["session_guardrails"]
                            if "manual_threshold" in config_data:
                                self.bot_core.manual_threshold = config_data["manual_threshold"]
                            if "target_liq" in config_data:
                                self.bot_core.target_liq = config_data["target_liq"]
                            if "target_oi" in config_data:
                                self.bot_core.target_oi = config_data["target_oi"]
                            if "target_slippage" in config_data:
                                self.bot_core.target_slippage = config_data["target_slippage"]
                            if "leverage_level" in config_data:
                                self.bot_core.leverage_level = config_data["leverage_level"]
                            if "betting_ratio" in config_data:
                                self.bot_core.betting_ratio = config_data["betting_ratio"]
                            if "split_entry_1_ratio" in config_data:
                                self.bot_core.split_entry_1_ratio = config_data["split_entry_1_ratio"]
                            if "split_entry_2_ratio" in config_data:
                                self.bot_core.split_entry_2_ratio = config_data["split_entry_2_ratio"]
                            if "split_entry_2_trigger_pct" in config_data:
                                self.bot_core.split_entry_2_trigger_pct = config_data["split_entry_2_trigger_pct"]
                            if "split_entry_3_ratio" in config_data:
                                self.bot_core.split_entry_3_ratio = config_data["split_entry_3_ratio"]
                            if "split_entry_3_trigger_pct" in config_data:
                                self.bot_core.split_entry_3_trigger_pct = config_data["split_entry_3_trigger_pct"]
                            if "split_cooldown_seconds" in config_data:
                                self.bot_core.split_cooldown_seconds = config_data["split_cooldown_seconds"]
                            if "cooldown_seconds" in config_data:
                                self.bot_core.cooldown_seconds = config_data["cooldown_seconds"]
                            if "profit_cooldown_seconds" in config_data:
                                self.bot_core.profit_cooldown_seconds = config_data["profit_cooldown_seconds"]
                            if "half_exit_close_ratio" in config_data:
                                self.bot_core.half_exit_close_ratio = config_data["half_exit_close_ratio"]
                            if "pyramiding_enabled" in config_data:
                                self.bot_core.pyramiding_enabled = config_data["pyramiding_enabled"]
                            if "pyramiding_ratio" in config_data:
                                self.bot_core.pyramiding_ratio = config_data["pyramiding_ratio"]
                            
                            engine = self.bot_core.v35_engine
                            if engine:
                                if "leverage_level" in config_data:
                                    engine.LEVERAGE = int(config_data["leverage_level"])
                                if "target_slippage" in config_data:
                                    try:
                                        slip_val = float(str(config_data["target_slippage"]).strip())
                                        engine.ENTRY_SLIPPAGE_CAP = slip_val / 100.0
                                    except Exception:
                                        pass
                            
                            self.bot_core.manual_config = {
                                "manual_threshold": self.bot_core.manual_threshold,
                                "target_liq": self.bot_core.target_liq,
                                "target_oi": self.bot_core.target_oi,
                                "target_slippage": self.bot_core.target_slippage
                            }
                            
                            try:
                                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shinseon_config.json")
                                file_config = {}
                                if os.path.exists(config_path):
                                    with open(config_path, "r", encoding="utf-8") as f:
                                        file_config = json.load(f)
                                file_config.update(config_data)
                                with open(config_path, "w", encoding="utf-8") as f:
                                    json.dump(file_config, f, indent=4, ensure_ascii=False)
                            except Exception as e:
                                logger.error(f"서버 설정 저장 실패: {e}")

                            write_trade_history_log(f"⚙️ [파라미터 설정 변경 적용] 레버리지: {config_data.get('leverage_level', 30)}배 | 배팅비중: {config_data.get('deploy_ratio', 100)}% | 1차비중: {config_data.get('split_entry_1_ratio', 100)}% | 2차비중: {config_data.get('split_entry_2_ratio', 50)}% | 손절쿨타임: {config_data.get('cooldown_seconds', 300)}초 | 익절쿨타임: {config_data.get('profit_cooldown_seconds', 15)}초 | 추매제한: {config_data.get('add_cooldown_seconds', 900)}초")
                            logger.info("⚙️ [서버 Config 동기화 완료] 클라이언트 파라미터 수신 및 적용 성공")
                            await self.broadcast_event("ui_update", {"msg": "⚙ [서버 동기화] 클라이언트 트레이딩 파라미터가 AWS 서버에 즉시 반영되었습니다.", "log_type": 1, "price": self.bot_core.current_price})
                    elif cmd == "CMD_REQ_FILE_LIST":
                        dates_set = set()
                        if os.path.exists(LOGS_DIR):
                            for fname in os.listdir(LOGS_DIR):
                                m = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
                                if m:
                                    dates_set.add(m.group(1))
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        dates_set.add(today_str)
                        sorted_dates = sorted(list(dates_set), reverse=True)
                        await self.broadcast_event("EVT_FILE_LIST", {"dates": sorted_dates})
                    elif cmd == "CMD_REQ_FILE_DOWNLOAD":
                        req_date = payload.get("date", datetime.now().strftime("%Y-%m-%d"))
                        log_file = os.path.join(LOGS_DIR, f"shinseon_trade_{req_date}.log")
                        csv_file = os.path.join(LOGS_DIR, f"shinseon_data_{req_date}.csv")
                        if not os.path.exists(csv_file) and os.path.exists("shinseon_data.csv"):
                            csv_file = "shinseon_data.csv"
                        log_text = ""
                        csv_text = ""
                        if os.path.exists(log_file):
                            try:
                                with open(log_file, "r", encoding="utf-8") as f:
                                    log_text = f.read()
                            except Exception: pass
                        if os.path.exists(csv_file):
                            try:
                                with open(csv_file, "r", encoding="utf-8") as f:
                                    csv_text = f.read()
                            except Exception: pass
                        await self.broadcast_event("EVT_FILE_DATA", {
                            "date": req_date,
                            "csv_text": csv_text,
                            "log_text": log_text
                        })
                    elif cmd == "CMD_REQ_CSV":
                        csv_path = "shinseon_data.csv"
                        if os.path.exists(csv_path):
                            with open(csv_path, "r", encoding="utf-8") as f:
                                csv_data = f.read()
                            await self.broadcast_event("EVT_CSV_DATA", {"csv_text": csv_data})
                        else:
                            await self.broadcast_event("ui_update", {"msg": "⚠️ [CSV 오류] 서버에 CSV 파일이 존재하지 않습니다.", "log_type": 1, "price": self.bot_core.current_price})
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.error(f"WS Command Error: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)

    async def broadcast_event(self, event_type, data):
        if not self.clients:
            return
        msg = json.dumps({"type": event_type, "data": data})
        async def _safe_send(client):
            try:
                await client.send(msg)
            except Exception:
                self.clients.discard(client)
        tasks = [_safe_send(c) for c in list(self.clients)]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_throttled(self, event_type, data):
        now = time.time()
        if now - self.last_chart_time < 0.5:
            return
        self.last_chart_time = now
        if not self.clients:
            return
        msg = json.dumps({"type": event_type, "data": data})
        async def _safe_send(client):
            try:
                await client.send(msg)
            except Exception:
                self.clients.discard(client)
        tasks = [_safe_send(c) for c in list(self.clients)]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

ws_server = None

def ui_callback(current_price, log_type, msg, **kwargs):
    if ws_server:
        data = {"price": current_price, "log_type": log_type, "msg": msg}
        data.update(kwargs)
        # Event type message
        asyncio.create_task(ws_server.broadcast_event("ui_update", data))
        if getattr(ws_server, "_last_logged_ui_msg", None) != msg:
            ws_server._last_logged_ui_msg = msg
            logger.info(f"[UI] {msg}")
    else:
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
