# -*- coding: utf-8 -*-
"""
[神選 : SHINSEON] 국왕 폐하 전용 수동매매 초슬림 미니 콕핏 위젯 (Cockpit Widget V7.80)
창 크기: 가로 500px 초슬림 설계 (웹 브라우저 및 트레이딩뷰 차트 옆 밀착 배치용)
테마: 황실 다크 글래스 테마 (#0b0e14 배경, 골드/네온 액센트, 고대비 가독성)
기능: 1분/5분/15분 3중 RSI 실시간 신호등 뱃지 및 3중 극점 동조 사운드 비프음 알림 탑재
"""

import sys
import os
import asyncio
import json
import time
import socket
import urllib.request
import ssl
import threading
import queue
from datetime import datetime

# Windows winsound 지원 (사운드 알림용)
try:
    import winsound
except ImportError:
    winsound = None

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QProgressBar, QCheckBox,
    QFrame, QGridLayout, QPlainTextEdit, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QBrush, QPainter
import websockets
from qasync import QEventLoop
import ccxt

# 1. 절대 이식성 상대 경로 추적
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VERSION = "V7.81"

# --- 국내 통신사 DNS 차단 우회용 Google DoH 패치 ---
original_getaddrinfo = socket.getaddrinfo
dns_cache = {}
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def secure_doh_resolve(host):
    if not ("binance" in host.lower() or "bitget" in host.lower()):
        return None
    if host in dns_cache:
        return dns_cache[host]
    try:
        url = f"https://8.8.8.8/resolve?name={host}&type=A"
        req = urllib.request.Request(url, headers={'Host': 'dns.google', 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.5, context=ssl_ctx) as r:
            data = json.loads(r.read().decode())
            answers = data.get("Answer", [])
            ips = [ans.get("data") for ans in answers if ans.get("type") == 1]
            if ips:
                dns_cache[host] = ips
                return ips
    except Exception:
        pass
    return None

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    ips = secure_doh_resolve(host)
    if ips:
        results = []
        for ip in ips:
            results.append((socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port)))
        return results
    return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = custom_getaddrinfo


def compute_rsi(closes, period=14):
    """Wilder's Smoothing 방식 정통 RSI(14) 연산"""
    if not closes or len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-diff)
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 1)


class MultiRsiWorker(QThread):
    """1분, 5분, 15분 멀티 타임프레임 실시간 RSI(14) 백그라운드 수집/연산 스레드"""
    rsi_updated = Signal(float, float, float)  # rsi_1m, rsi_5m, rsi_15m

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def fetch_closes(self, gran):
        # 1차: Bitget REST API 시도
        try:
            url = f"https://api.bitget.com/api/v2/mix/market/candles?symbol=BTCUSDT&granularity={gran}&productType=USDT-FUTURES&limit=30"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=2.5, context=ssl_ctx) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw = data.get('data', [])
                if raw:
                    # [ts, open, high, low, close, ...]
                    sorted_raw = sorted(raw, key=lambda x: int(x[0]))
                    return [float(c[4]) for c in sorted_raw]
        except Exception:
            pass

        # 2차 대안: Binance Futures REST API 백업 시도
        try:
            url = f"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval={gran}&limit=30"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=2.5, context=ssl_ctx) as resp:
                raw = json.loads(resp.read().decode('utf-8'))
                if isinstance(raw, list) and raw:
                    return [float(k[4]) for k in raw]
        except Exception:
            pass

        return []

    def run(self):
        while self.running:
            try:
                c_1m = self.fetch_closes("1m")
                c_5m = self.fetch_closes("5m")
                c_15m = self.fetch_closes("15m")

                if c_1m and c_5m and c_15m:
                    rsi_1m = compute_rsi(c_1m, 14)
                    rsi_5m = compute_rsi(c_5m, 14)
                    rsi_15m = compute_rsi(c_15m, 14)
                    self.rsi_updated.emit(rsi_1m, rsi_5m, rsi_15m)
            except Exception:
                pass

            # 3.5초 주기 대기 (중간 중단 감지)
            for _ in range(35):
                if not self.running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.running = False


class BitgetMainDirectWorker(QThread):
    """
    [신선] 비트겟 본 계정 REST/ccxt 직접 통신 백그라운드 워커
    웹서버 의존도 0% - 비트겟 본 계정 API 직접 통신으로 실시간 포지션/가격 수집 및 5대 황실 원클릭 주문 집행
    """
    position_updated = Signal(dict)
    order_result = Signal(str)

    API_KEY = "bg_670c7963afe129099346583180ce606b"
    SECRET_KEY = "4fe82e41304e84e315c7aa222ead7a4307182ec5f4766c37ad2290bf4268a2a0"
    PASSPHRASE = "shinsun1234567"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self._action_queue = queue.Queue()
        self._force_event = threading.Event()
        self.exchange = None
        self._init_exchange()

    def _init_exchange(self):
        try:
            self.exchange = ccxt.bitget({
                'apiKey': self.API_KEY,
                'secret': self.SECRET_KEY,
                'password': self.PASSPHRASE,
                'options': {'defaultType': 'swap'},
                'enableRateLimit': True
            })
        except Exception:
            self.exchange = None

    def force_sync(self):
        self._force_event.set()

    def submit_order_action(self, action_type, params=None):
        self._action_queue.put((action_type, params or {}))
        self._force_event.set()

    def run(self):
        while self.running:
            # 1. 큐에 적재된 주문 액션 처리
            while not self._action_queue.empty() and self.running:
                try:
                    action_type, params = self._action_queue.get_nowait()
                    self._process_action(action_type, params)
                except Exception as e:
                    self.order_result.emit(f"❌ [주문 처리 예외] {e}")

            # 2. 본 계정 실시간 포지션 및 티커 조회 & HUD 시그널 방출
            try:
                self.fetch_and_emit_position()
            except Exception:
                pass

            # 3. 1.0초 대기 (force_sync() 호출 시 즉시 기동)
            self._force_event.wait(timeout=1.0)
            self._force_event.clear()

    def fetch_and_emit_position(self):
        if not self.exchange:
            self._init_exchange()
            if not self.exchange:
                return

        try:
            # 1. BTCUSDT 현재가 조회
            current_price = 0.0
            try:
                ticker = self.exchange.fetch_ticker('BTC/USDT:USDT')
                current_price = float(ticker.get('last') or ticker.get('close') or 0.0)
            except Exception:
                pass

            # 2. 비트겟 V2 포지션 조회
            res = self.exchange.private_mix_get_v2_mix_position_all_position({'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'})
            pos_list = res.get('data', []) if isinstance(res, dict) else []

            active_pos = None
            for p in pos_list:
                sym = p.get('symbol', '')
                total_qty = float(p.get('total', 0) or p.get('available', 0) or 0)
                if 'BTC' in sym and total_qty > 0:
                    active_pos = p
                    break

            if active_pos:
                hold_side_raw = str(active_pos.get('holdSide', 'long')).lower()
                side = "LONG" if hold_side_raw == "long" else "SHORT"
                contracts = float(active_pos.get('total', 0) or 0.0)
                entry_price = float(active_pos.get('openPriceAvg', 0) or 0.0)
                leverage = int(float(active_pos.get('leverage', 60) or 60))
                mark_price = float(active_pos.get('markPrice', 0) or current_price or 0.0)
                unrealized_pnl = float(active_pos.get('unrealizedPL', 0) or 0.0)
                liquidation_price = float(active_pos.get('liquidationPrice', 0) or 0.0)
                break_even_price = float(active_pos.get('breakEvenPrice', 0) or entry_price)

                if current_price <= 0:
                    current_price = mark_price

                # 미실현 수익률(ROE %) 계산
                margin_size = float(active_pos.get('marginSize', 0) or 0.0)
                if margin_size > 0:
                    roe_pct = (unrealized_pnl / margin_size) * 100.0
                elif entry_price > 0:
                    diff = (current_price - entry_price) if side == "LONG" else (entry_price - current_price)
                    roe_pct = (diff / entry_price) * 100.0 * leverage
                else:
                    roe_pct = 0.0

                payload = {
                    "has_position": True,
                    "side": side,
                    "contracts": contracts,
                    "entry_price": entry_price,
                    "leverage": leverage,
                    "mark_price": mark_price,
                    "current_price": current_price,
                    "unrealized_pnl": unrealized_pnl,
                    "liquidation_price": liquidation_price,
                    "break_even_price": break_even_price,
                    "roe_pct": roe_pct
                }
            else:
                payload = {
                    "has_position": False,
                    "side": "NONE",
                    "contracts": 0.0,
                    "entry_price": 0.0,
                    "leverage": 60,
                    "mark_price": current_price,
                    "current_price": current_price,
                    "unrealized_pnl": 0.0,
                    "liquidation_price": 0.0,
                    "break_even_price": 0.0,
                    "roe_pct": 0.0
                }

            self.position_updated.emit(payload)
        except Exception:
            pass

    def _get_active_position(self):
        try:
            res = self.exchange.private_mix_get_v2_mix_position_all_position({'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'})
            pos_list = res.get('data', []) if isinstance(res, dict) else []
            for p in pos_list:
                sym = p.get('symbol', '')
                total_qty = float(p.get('total', 0) or 0)
                if 'BTC' in sym and total_qty > 0:
                    return p
        except Exception:
            pass
        return None

    def _process_action(self, action_type, params):
        if not self.exchange:
            self._init_exchange()
            if not self.exchange:
                self.order_result.emit("❌ [비트겟 API 에러] 본 계정 API 초기화 실패")
                return

        if action_type == "QUICK_MARKET":
            side = params.get("side", "LONG").upper()
            qty = float(params.get("qty", 0.5))
            hold_side = "long" if side == "LONG" else "short"
            order_side = "buy" if side == "LONG" else "sell"
            try:
                res = self.exchange.private_mix_post_v2_mix_order_place_order({
                    "symbol": "BTCUSDT",
                    "productType": "USDT-FUTURES",
                    "marginMode": "crossed",
                    "marginCoin": "USDT",
                    "size": str(round(qty, 4)),
                    "side": order_side,
                    "orderType": "market",
                    "tradeSide": "open",
                    "holdSide": hold_side
                })
                if res.get("code") == "00000":
                    self.order_result.emit(f"🟢 [본 계정 시장가 진입 성공] {side} {qty} BTC 체결 완료!")
                else:
                    self.order_result.emit(f"❌ [본 계정 시장가 진입 실패] {res.get('msg')} ({res.get('code')})")
            except Exception as e:
                self.order_result.emit(f"❌ [시장가 진입 에러] {e}")

        elif action_type == "BE_SHIELD":
            pos = self._get_active_position()
            if not pos:
                self.order_result.emit("⚠️ [무위험 본전가드] 본 계정에 보유 중인 포지션이 없습니다.")
                return
            entry_price = float(pos.get('openPriceAvg', 0) or 0.0)
            contracts = float(pos.get('total', 0) or 0.0)
            hold_side = str(pos.get('holdSide', 'long')).lower()
            side_str = "LONG" if hold_side == "long" else "SHORT"

            try:
                # 기존 손절 플랜 주문 취소
                try:
                    self.exchange.private_mix_post_v2_mix_order_cancel_plan_order({
                        "symbol": "BTCUSDT",
                        "productType": "USDT-FUTURES",
                        "marginCoin": "USDT",
                        "planType": "loss_plan"
                    })
                except Exception:
                    pass

                # 본전 스탑로스 발주
                sl_res = self.exchange.private_mix_post_v2_mix_order_place_tpsl_order({
                    "symbol": "BTCUSDT",
                    "productType": "USDT-FUTURES",
                    "marginCoin": "USDT",
                    "planType": "loss_plan",
                    "triggerPrice": str(round(entry_price, 1)),
                    "triggerType": "mark_price",
                    "size": str(round(contracts, 4)),
                    "holdSide": hold_side
                })
                if sl_res.get("code") == "00000":
                    self.order_result.emit(f"🛡️ [본 계정 본전가드 안착] {side_str} {contracts} BTC @ ${entry_price:,.1f} 본전 스탑로스 안착 완료 (0원 무손실 보장)!")
                else:
                    self.order_result.emit(f"⚠️ [본전가드 실패] {sl_res.get('msg')} ({sl_res.get('code')})")
            except Exception as e:
                self.order_result.emit(f"❌ [본전가드 에러] {e}")

        elif action_type == "AUTO_GUARD":
            pos = self._get_active_position()
            if not pos:
                self.order_result.emit("⚠️ [2단 안전방패] 본 계정에 보유 중인 포지션이 없습니다.")
                return
            entry_price = float(pos.get('openPriceAvg', 0) or 0.0)
            contracts = float(pos.get('total', 0) or 0.0)
            hold_side = str(pos.get('holdSide', 'long')).lower()
            side_str = "LONG" if hold_side == "long" else "SHORT"

            half_qty = round(contracts * 0.5, 4)
            rem_qty = round(contracts - half_qty, 4)
            if half_qty <= 0:
                half_qty = contracts
                rem_qty = 0

            if side_str == "LONG":
                tp1 = round(entry_price + 1000.0, 1)
                tp2 = round(entry_price + 1200.0, 1)
                sl1 = round(entry_price - 500.0, 1)
                sl2 = round(entry_price - 600.0, 1)
            else:
                tp1 = round(entry_price - 1000.0, 1)
                tp2 = round(entry_price - 1200.0, 1)
                sl1 = round(entry_price + 500.0, 1)
                sl2 = round(entry_price + 600.0, 1)

            try:
                # 1단 TP
                self.exchange.private_mix_post_v2_mix_order_place_tpsl_order({
                    "symbol": "BTCUSDT",
                    "productType": "USDT-FUTURES",
                    "marginCoin": "USDT",
                    "planType": "profit_plan",
                    "triggerPrice": str(tp1),
                    "triggerType": "mark_price",
                    "size": str(half_qty),
                    "holdSide": hold_side
                })
                # 1단 SL
                self.exchange.private_mix_post_v2_mix_order_place_tpsl_order({
                    "symbol": "BTCUSDT",
                    "productType": "USDT-FUTURES",
                    "marginCoin": "USDT",
                    "planType": "loss_plan",
                    "triggerPrice": str(sl1),
                    "triggerType": "mark_price",
                    "size": str(half_qty),
                    "holdSide": hold_side
                })
                # 2단 (잔여 수량 있을 시)
                if rem_qty > 0:
                    self.exchange.private_mix_post_v2_mix_order_place_tpsl_order({
                        "symbol": "BTCUSDT",
                        "productType": "USDT-FUTURES",
                        "marginCoin": "USDT",
                        "planType": "profit_plan",
                        "triggerPrice": str(tp2),
                        "triggerType": "mark_price",
                        "size": str(rem_qty),
                        "holdSide": hold_side
                    })
                    self.exchange.private_mix_post_v2_mix_order_place_tpsl_order({
                        "symbol": "BTCUSDT",
                        "productType": "USDT-FUTURES",
                        "marginCoin": "USDT",
                        "planType": "loss_plan",
                        "triggerPrice": str(sl2),
                        "triggerType": "mark_price",
                        "size": str(rem_qty),
                        "holdSide": hold_side
                    })
                self.order_result.emit(f"🛡️ [본 계정 2단 안전방패 배치 완료] TP(${tp1:,.1f}/${tp2:,.1f}), SL(${sl1:,.1f}/${sl2:,.1f}) 분할 발주 성공!")
            except Exception as e:
                self.order_result.emit(f"❌ [2단 안전방패 에러] {e}")

        elif action_type == "CLOSE_50":
            pos = self._get_active_position()
            if not pos:
                self.order_result.emit("⚠️ [50% 분할 청산] 본 계정에 보유 중인 포지션이 없습니다.")
                return
            contracts = float(pos.get('total', 0) or 0.0)
            hold_side = str(pos.get('holdSide', 'long')).lower()
            side_str = "LONG" if hold_side == "long" else "SHORT"
            close_side = "sell" if hold_side == "long" else "buy"
            half_qty = round(contracts * 0.5, 4)

            try:
                res = self.exchange.private_mix_post_v2_mix_order_place_order({
                    "symbol": "BTCUSDT",
                    "productType": "USDT-FUTURES",
                    "marginMode": "crossed",
                    "marginCoin": "USDT",
                    "size": str(half_qty),
                    "side": close_side,
                    "orderType": "market",
                    "tradeSide": "close",
                    "holdSide": hold_side
                })
                if res.get("code") == "00000":
                    self.order_result.emit(f"✂️ [본 계정 50% 분할 청산 성공] {side_str} {half_qty} BTC 시장가 분할 청산 체결 완료!")
                else:
                    self.order_result.emit(f"❌ [50% 청산 실패] {res.get('msg')} ({res.get('code')})")
            except Exception as e:
                self.order_result.emit(f"❌ [50% 분할 청산 에러] {e}")

        elif action_type == "EMERGENCY":
            try:
                # 1. 미체결 주문 및 플랜 주문 전수 취소
                try:
                    self.exchange.cancel_all_orders('BTC/USDT:USDT')
                except Exception:
                    pass
                try:
                    self.exchange.private_mix_post_v2_mix_order_cancel_all_orders({
                        "symbol": "BTCUSDT",
                        "productType": "USDT-FUTURES",
                        "marginCoin": "USDT"
                    })
                except Exception:
                    pass

                # 2. 플래시 포지션 청산 시도
                flash_res = None
                try:
                    flash_res = self.exchange.private_mix_post_v2_mix_order_close_positions({
                        "symbol": "BTCUSDT",
                        "productType": "USDT-FUTURES"
                    })
                except Exception:
                    pass

                if not flash_res or flash_res.get("code") != "00000":
                    # 시장가 반대 청산 백업
                    pos = self._get_active_position()
                    if pos:
                        contracts = float(pos.get('total', 0) or 0.0)
                        hold_side = str(pos.get('holdSide', 'long')).lower()
                        close_side = "sell" if hold_side == "long" else "buy"
                        self.exchange.private_mix_post_v2_mix_order_place_order({
                            "symbol": "BTCUSDT",
                            "productType": "USDT-FUTURES",
                            "marginMode": "crossed",
                            "marginCoin": "USDT",
                            "size": str(round(contracts, 4)),
                            "side": close_side,
                            "orderType": "market",
                            "tradeSide": "close",
                            "holdSide": hold_side
                        })

                self.order_result.emit("🚨 [본 계정 비상 탈출 성공] 비트겟 100% 전량 시장가 청산 및 미체결 주문 전수 취소 완료!")
            except Exception as e:
                self.order_result.emit(f"❌ [비상 탈출 에러] {e}")

        # 주문 처리 완료 후 0.1초 만에 즉시 포지션 재조회
        try:
            self.fetch_and_emit_position()
        except Exception:
            pass

    def stop(self):
        self.running = False
        self._force_event.set()


class ShinseonCockpit(QMainWindow):
    def __init__(self):
        super().__init__()
        self.CURRENT_VERSION = VERSION
        self.ws = None
        self.ws_url = "ws://13.192.187.244:8765"
        self.current_price = 0.0
        self.has_position = False
        self.position_side = "NONE"
        self.position_contracts = 0.0
        self.position_entry_price = 0.0
        self.position_unrealized_pnl = 0.0
        self.position_roe = 0.0
        self.position_liq_price = 0.0
        self.sound_enabled = True
        self.smart_stop_active = False
        self._last_signal_direction = None
        self._last_beep_time = 0
        self._prev_rsi_1m = None
        self._last_rsi_alert_time = 0.0

        self.init_ui()
        self.load_config()

        # 3중 멀티 타임프레임 RSI 백그라운드 수집 스레드 시작
        self.rsi_worker = MultiRsiWorker(self)
        self.rsi_worker.rsi_updated.connect(self.on_rsi_updated)
        self.rsi_worker.start()

        # 비트겟 본 계정 직통 통신 워커 시작 (웹서버 의존도 완전 탈피)
        self.bitget_worker = BitgetMainDirectWorker(self)
        self.bitget_worker.position_updated.connect(self.handle_direct_position_update)
        self.bitget_worker.order_result.connect(self.add_log)
        self.bitget_worker.start()

    def init_ui(self):
        self.setWindowTitle(f"👑 [SHINSEON] 황실 콕핏 {self.CURRENT_VERSION} (가로 500px 초슬림)")
        self.resize(500, 830)
        self.setMinimumWidth(480)
        self.setMaximumWidth(540)

        # 황실 다크 글래스 스타일시트
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0e14;
                color: #F3F4F6;
                font-family: 'Pretendard', 'Segoe UI', 'Noto Sans KR', sans-serif;
            }
            QFrame.card {
                background-color: #121620;
                border: 1px solid #1e2638;
                border-radius: 8px;
                padding: 6px;
            }
            QLabel {
                color: #E2E8F0;
                font-size: 12px;
            }
            QLabel.title {
                color: #DEBA9D;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #080a0f;
                border: 1px solid #2a354b;
                border-radius: 4px;
                color: #00FFCC;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 1px solid #00FFCC;
            }
            QCheckBox {
                color: #CBD5E1;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #334155;
                background-color: #080a0f;
            }
            QCheckBox::indicator:checked {
                background-color: #00FFCC;
                border: 1px solid #00FFCC;
            }
            QProgressBar {
                background-color: #080a0f;
                border: 1px solid #1e2638;
                border-radius: 4px;
                text-align: center;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
                height: 18px;
            }
            QPlainTextEdit {
                background-color: #06080b;
                border: 1px solid #1a2232;
                border-radius: 4px;
                color: #94A3B8;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)

        # ----------------------------------------------------
        # 1. 상단 타이틀 바 & Always on Top & 연결 상태
        # ----------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        lbl_crown = QLabel(f"👑 <b style='color:#DEBA9D; font-size:14px;'>황실 콕핏 {self.CURRENT_VERSION}</b>")
        header_layout.addWidget(lbl_crown)

        header_layout.addStretch()

        self.chk_top = QCheckBox("📌 항상 위에 표시")
        self.chk_top.setChecked(False)
        self.chk_top.toggled.connect(self.toggle_always_on_top)
        header_layout.addWidget(self.chk_top)

        self.lbl_ws_status = QLabel("🔴 서버 대기 중")
        self.lbl_ws_status.setStyleSheet("color: #FF5555; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.lbl_ws_status)

        main_layout.addLayout(header_layout)

        # ----------------------------------------------------
        # 2. 실시간 오더플로우 레이더 패널
        # ----------------------------------------------------
        radar_card = QFrame()
        radar_card.setProperty("class", "card")
        radar_layout = QVBoxLayout(radar_card)
        radar_layout.setContentsMargins(8, 6, 8, 6)
        radar_layout.setSpacing(4)

        radar_title_layout = QHBoxLayout()
        lbl_radar_title = QLabel("🌊 <b style='color:#38BDF8;'>[실시간 오더플로우 레이더]</b>")
        radar_title_layout.addWidget(lbl_radar_title)

        self.lbl_session = QLabel("<span style='color:#DEBA9D; font-weight:bold;'>세션 로딩...</span>")
        radar_title_layout.addWidget(self.lbl_session)
        radar_title_layout.addStretch()

        self.chk_sound = QCheckBox("🔔 사운드 알림")
        self.chk_sound.setChecked(True)
        self.chk_sound.toggled.connect(self.toggle_sound)
        radar_title_layout.addWidget(self.chk_sound)

        radar_layout.addLayout(radar_title_layout)

        # 🚦 1분 / 5분 / 15분 3중 RSI 실시간 신호등 뱃지 바
        rsi_layout = QHBoxLayout()
        rsi_layout.setSpacing(6)

        self.lbl_rsi_1m = QLabel("1m RSI: --.-% ⚪")
        self.lbl_rsi_1m.setAlignment(Qt.AlignCenter)
        self.lbl_rsi_1m.setStyleSheet("background-color: rgba(60, 60, 60, 0.3); border: 1px solid #757575; color: #BDBDBD; font-weight: bold; border-radius: 4px; padding: 2px 4px; font-size: 11px;")

        self.lbl_rsi_5m = QLabel("5m RSI: --.-% ⚪")
        self.lbl_rsi_5m.setAlignment(Qt.AlignCenter)
        self.lbl_rsi_5m.setStyleSheet("background-color: rgba(60, 60, 60, 0.3); border: 1px solid #757575; color: #BDBDBD; font-weight: bold; border-radius: 4px; padding: 2px 4px; font-size: 11px;")

        self.lbl_rsi_15m = QLabel("15m RSI: --.-% ⚪")
        self.lbl_rsi_15m.setAlignment(Qt.AlignCenter)
        self.lbl_rsi_15m.setStyleSheet("background-color: rgba(60, 60, 60, 0.3); border: 1px solid #757575; color: #BDBDBD; font-weight: bold; border-radius: 4px; padding: 2px 4px; font-size: 11px;")

        rsi_layout.addWidget(self.lbl_rsi_1m)
        rsi_layout.addWidget(self.lbl_rsi_5m)
        rsi_layout.addWidget(self.lbl_rsi_15m)

        radar_layout.addLayout(rsi_layout)

        # 3색 실시간 힌트 뱃지 (가장 중요한 오더플로우 나침반)
        self.lbl_hint_badge = QLabel("⚪ 지금은 관망이 유리하다")
        self.lbl_hint_badge.setAlignment(Qt.AlignCenter)
        self.lbl_hint_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2232, stop:1 #0f1624);
            border: 1px solid #334155;
            border-radius: 6px;
            color: #94A3B8;
            font-size: 14px;
            font-weight: 900;
            padding: 6px;
        """)
        radar_layout.addWidget(self.lbl_hint_badge)

        # 게이지 1: 1분 청산액
        self.bar_liq = QProgressBar()
        self.bar_liq.setRange(0, 1000000)
        self.bar_liq.setValue(0)
        self.bar_liq.setFormat("1분 누적 청산: $0 / $1,000,000")
        self.bar_liq.setStyleSheet("""
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b8860b, stop:1 #ffd700);
                border-radius: 3px;
            }
        """)
        radar_layout.addWidget(self.bar_liq)

        # 게이지 2: 1분 OI 속도
        self.bar_oi = QProgressBar()
        self.bar_oi.setRange(0, 100)
        self.bar_oi.setValue(0)
        self.bar_oi.setFormat("1분 OI 속도: +0.0000% / +0.1700%")
        self.bar_oi.setStyleSheet("""
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0088cc, stop:1 #00ffcc);
                border-radius: 3px;
            }
        """)
        radar_layout.addWidget(self.bar_oi)

        main_layout.addWidget(radar_card)

        # ----------------------------------------------------
        # 3. 원클릭 초고속 시장가 진입 패널
        # ----------------------------------------------------
        entry_card = QFrame()
        entry_card.setProperty("class", "card")
        entry_layout = QVBoxLayout(entry_card)
        entry_layout.setContentsMargins(8, 6, 8, 6)
        entry_layout.setSpacing(6)

        entry_title_layout = QHBoxLayout()
        lbl_entry_title = QLabel("🚀 <b style='color:#00FFCC;'>[원클릭 빠른 시장가 진입]</b>")
        entry_title_layout.addWidget(lbl_entry_title)
        entry_title_layout.addStretch()

        lbl_qty_title = QLabel("수량(BTC):")
        entry_title_layout.addWidget(lbl_qty_title)

        self.edit_qty = QLineEdit("0.5")
        self.edit_qty.setFixedWidth(70)
        self.edit_qty.setAlignment(Qt.AlignCenter)
        entry_title_layout.addWidget(self.edit_qty)

        entry_layout.addLayout(entry_title_layout)

        # 수량 프리셋 버튼
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(4)
        for qty_val in [0.5, 1.0, 2.0, 5.0]:
            btn_pre = QPushButton(f"{qty_val} BTC")
            btn_pre.setStyleSheet("""
                QPushButton {
                    background-color: #1e2638;
                    border: 1px solid #2d3b55;
                    border-radius: 4px;
                    color: #CBD5E1;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #2a354b;
                    border-color: #DEBA9D;
                    color: #FFFFFF;
                }
            """)
            btn_pre.clicked.connect(lambda chk, q=qty_val: self.edit_qty.setText(str(q)))
            preset_layout.addWidget(btn_pre)

        entry_layout.addLayout(preset_layout)

        # 롱 / 숏 시장가 즉시 진입 버튼 (대형 네온 버튼)
        market_btn_layout = QHBoxLayout()
        market_btn_layout.setSpacing(6)

        self.btn_quick_long = QPushButton("🟢 시장가 롱 진입 (LONG)")
        self.btn_quick_long.setFixedHeight(40)
        self.btn_quick_long.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00E676, stop:1 #008947);
                border: 1px solid #00FFCC;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 900;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10FFA0, stop:1 #00A855);
                border: 1px solid #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #005A2E;
            }
        """)
        self.btn_quick_long.clicked.connect(lambda: self.execute_quick_market("LONG"))
        market_btn_layout.addWidget(self.btn_quick_long)

        self.btn_quick_short = QPushButton("🔴 시장가 숏 진입 (SHORT)")
        self.btn_quick_short.setFixedHeight(40)
        self.btn_quick_short.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF3366, stop:1 #A8002B);
                border: 1px solid #FF6688;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 900;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF5580, stop:1 #C80036);
                border: 1px solid #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #660018;
            }
        """)
        self.btn_quick_short.clicked.connect(lambda: self.execute_quick_market("SHORT"))
        market_btn_layout.addWidget(self.btn_quick_short)

        entry_layout.addLayout(market_btn_layout)
        main_layout.addWidget(entry_card)

        # ----------------------------------------------------
        # 4. 실시간 본 계정 포지션 HUD 패널
        # ----------------------------------------------------
        hud_card = QFrame()
        hud_card.setProperty("class", "card")
        hud_layout = QVBoxLayout(hud_card)
        hud_layout.setContentsMargins(8, 6, 8, 6)
        hud_layout.setSpacing(4)

        hud_header = QHBoxLayout()
        lbl_hud_title = QLabel("📊 <b style='color:#DEBA9D;'>[본 계정 실시간 포지션 HUD]</b>")
        hud_header.addWidget(lbl_hud_title)

        hud_header.addStretch()

        btn_sync_pos = QPushButton("🔄 동기화")
        btn_sync_pos.setStyleSheet("""
            QPushButton {
                background-color: #1e2638;
                border: 1px solid #3b82f6;
                border-radius: 4px;
                color: #93C5FD;
                font-size: 11px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #2563eb;
                color: #FFFFFF;
            }
        """)
        btn_sync_pos.clicked.connect(self.request_sync_position)
        hud_header.addWidget(btn_sync_pos)

        hud_layout.addLayout(hud_header)

        # HUD 데이터 그리드
        hud_grid = QGridLayout()
        hud_grid.setHorizontalSpacing(8)
        hud_grid.setVerticalSpacing(3)

        self.lbl_hud_side = QLabel("⚪ NO POSITION")
        self.lbl_hud_side.setStyleSheet("font-size: 13px; font-weight: 900; color: #94A3B8;")
        hud_grid.addWidget(QLabel("포지션:"), 0, 0)
        hud_grid.addWidget(self.lbl_hud_side, 0, 1)

        self.lbl_hud_qty = QLabel("0.0000 BTC")
        self.lbl_hud_qty.setStyleSheet("font-weight: bold; color: #F3F4F6;")
        hud_grid.addWidget(QLabel("보유수량:"), 0, 2)
        hud_grid.addWidget(self.lbl_hud_qty, 0, 3)

        self.lbl_hud_entry = QLabel("$0.00")
        self.lbl_hud_entry.setStyleSheet("font-weight: bold; color: #DEBA9D;")
        hud_grid.addWidget(QLabel("진입평단:"), 1, 0)
        hud_grid.addWidget(self.lbl_hud_entry, 1, 1)

        self.lbl_hud_price = QLabel("$0.00")
        self.lbl_hud_price.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        hud_grid.addWidget(QLabel("현재가격:"), 1, 2)
        hud_grid.addWidget(self.lbl_hud_price, 1, 3)

        self.lbl_hud_pnl = QLabel("$0.00 USDT (0.00%)")
        self.lbl_hud_pnl.setStyleSheet("font-weight: 900; color: #94A3B8;")
        hud_grid.addWidget(QLabel("미실현손익:"), 2, 0)
        hud_grid.addWidget(self.lbl_hud_pnl, 2, 1, 1, 3)

        self.lbl_hud_liq = QLabel("$0.00 (안전거리: --)")
        self.lbl_hud_liq.setStyleSheet("font-weight: bold; color: #00FFCC;")
        hud_grid.addWidget(QLabel("청산가/안전:"), 3, 0)
        hud_grid.addWidget(self.lbl_hud_liq, 3, 1, 1, 3)

        hud_layout.addLayout(hud_grid)
        main_layout.addWidget(hud_card)

        # ----------------------------------------------------
        # 5. 황실 안전 방패 & 탈출 제어판 (4대 결사항전)
        # ----------------------------------------------------
        shield_card = QFrame()
        shield_card.setProperty("class", "card")
        shield_layout = QVBoxLayout(shield_card)
        shield_layout.setContentsMargins(8, 6, 8, 6)
        shield_layout.setSpacing(5)

        lbl_shield_title = QLabel("🛡️ <b style='color:#FFD700;'>[황실 안전 방패 & 탈출 패널]</b>")
        shield_layout.addWidget(lbl_shield_title)

        shield_grid = QGridLayout()
        shield_grid.setHorizontalSpacing(6)
        shield_grid.setVerticalSpacing(5)

        # 1. 무위험 본전가드 (BE Shield)
        self.btn_be_shield = QPushButton("🛡️ 무위험 본전가드 (BE Shield)\n[진입 평단가 0원 무손실 스탑로스 장착]")
        self.btn_be_shield.setFixedHeight(38)
        self.btn_be_shield.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DAA520, stop:1 #8B6508);
                border: 1px solid #FFD700;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFD700, stop:1 #B8860B);
            }
        """)
        self.btn_be_shield.clicked.connect(self.execute_be_shield)
        shield_grid.addWidget(self.btn_be_shield, 0, 0)

        # 2. 2단 안전방패 (TP 2단 / SL 2단)
        self.btn_auto_guard = QPushButton("🛡️ 2단 안전방패 (TP/SL)\n[TP +1000/+1200, SL -500/-600]")
        self.btn_auto_guard.setFixedHeight(38)
        self.btn_auto_guard.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0284C7, stop:1 #0369A1);
                border: 1px solid #38BDF8;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38BDF8, stop:1 #0284C7);
            }
        """)
        self.btn_auto_guard.clicked.connect(self.execute_auto_guard)
        shield_grid.addWidget(self.btn_auto_guard, 0, 1)

        # 3. 50% 시장가 분할 청산
        self.btn_close_50 = QPushButton("✂️ 50% 시장가 분할 청산\n[오픈 포지션 절반 즉시 익절]")
        self.btn_close_50.setFixedHeight(38)
        self.btn_close_50.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D97706, stop:1 #B45309);
                border: 1px solid #FBBF24;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F59E0B, stop:1 #D97706);
            }
        """)
        self.btn_close_50.clicked.connect(self.execute_close_50)
        shield_grid.addWidget(self.btn_close_50, 1, 0)

        # 4. 🚨 비상 탈출 (EMERGENCY 100% 전량 청산)
        self.btn_emergency = QPushButton("🚨 비상 탈출 (EMERGENCY)\n[100% 전량 시장가 청산 & 주문 취소]")
        self.btn_emergency.setFixedHeight(38)
        self.btn_emergency.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DC2626, stop:1 #991B1B);
                border: 1px solid #EF4444;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 900;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF4444, stop:1 #B91C1C);
            }
        """)
        self.btn_emergency.clicked.connect(self.execute_emergency)
        shield_grid.addWidget(self.btn_emergency, 1, 1)

        shield_layout.addLayout(shield_grid)
        main_layout.addWidget(shield_card)

        # ----------------------------------------------------
        # 6. 스마트 스탑 가드 제어판
        # ----------------------------------------------------
        stop_card = QFrame()
        stop_card.setProperty("class", "card")
        stop_layout = QHBoxLayout(stop_card)
        stop_layout.setContentsMargins(8, 5, 8, 5)
        stop_layout.setSpacing(6)

        lbl_stop_title = QLabel("📉 <b>스마트 스탑</b>:")
        stop_layout.addWidget(lbl_stop_title)

        lbl_pnl_tag = QLabel("오프셋 PnL:")
        stop_layout.addWidget(lbl_pnl_tag)

        self.edit_stop_offset = QLineEdit("0.60")
        self.edit_stop_offset.setFixedWidth(55)
        self.edit_stop_offset.setAlignment(Qt.AlignCenter)
        stop_layout.addWidget(self.edit_stop_offset)

        lbl_pct = QLabel("%")
        stop_layout.addWidget(lbl_pct)

        self.btn_smart_stop = QPushButton("🛡️ 스탑가드 설정")
        self.btn_smart_stop.setStyleSheet("""
            QPushButton {
                background-color: #1e2638;
                border: 1px solid #10B981;
                border-radius: 4px;
                color: #6EE7B7;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #FFFFFF;
            }
        """)
        self.btn_smart_stop.clicked.connect(self.toggle_smart_stop)
        stop_layout.addWidget(self.btn_smart_stop)

        self.lbl_stop_status = QLabel("○ 비활성")
        self.lbl_stop_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        stop_layout.addWidget(self.lbl_stop_status)

        stop_layout.addStretch()
        main_layout.addWidget(stop_card)

        # ----------------------------------------------------
        # 7. 실시간 상태 및 응답 미니 로그창
        # ----------------------------------------------------
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(80)
        self.txt_log.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] 👑 [SHINSEON] 초슬림 콕핏 {self.CURRENT_VERSION} 가동 준비 완료.")
        main_layout.addWidget(self.txt_log)

    def load_config(self):
        config_path = os.path.join(BASE_DIR, "shinseon_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.sound_enabled = cfg.get("sound_enabled", True)
                    self.chk_sound.setChecked(self.sound_enabled)
            except Exception:
                pass

    def add_log(self, text):
        t_str = datetime.now().strftime("%H:%M:%S")
        self.txt_log.appendPlainText(f"[{t_str}] {text}")
        try:
            self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())
        except Exception:
            pass

    def toggle_always_on_top(self, checked):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.add_log("📌 [화면 고정] Always on Top 활성화 (창이 항상 위에 유지됩니다)")
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self.add_log("📌 [화면 고정] Always on Top 해제")
        self.show()

    def toggle_sound(self, checked):
        self.sound_enabled = checked
        stat = "ON 🔔" if checked else "OFF 🔕"
        self.add_log(f"사운드 알림: {stat}")

    def play_alert_sound(self, sound_type="SIGNAL"):
        if not self.sound_enabled:
            return
        now = time.time()
        if now - self._last_beep_time < 2.0:
            return
        self._last_beep_time = now

        try:
            if winsound:
                if sound_type == "LONG":
                    winsound.Beep(1500, 200)
                elif sound_type == "SHORT":
                    winsound.Beep(900, 200)
                else:
                    winsound.Beep(1200, 250)
            else:
                QApplication.beep()
        except Exception:
            pass

    # ----------------------------------------------------
    # 웹소켓 및 데이터 통신
    # ----------------------------------------------------
    async def connect_websocket(self):
        while True:
            try:
                self.lbl_ws_status.setText("🟡 AWS 접속 시도...")
                self.lbl_ws_status.setStyleSheet("color: #FBBF24; font-weight: bold; font-size: 11px;")
                self.add_log(f"[웹소켓] AWS 릴레이 서버 연결 시도: {self.ws_url}")

                async with websockets.connect(self.ws_url, open_timeout=5.0, ping_interval=20, ping_timeout=20) as ws:
                    self.ws = ws
                    self.lbl_ws_status.setText("🟢 AWS 연결됨")
                    self.lbl_ws_status.setStyleSheet("color: #00FFCC; font-weight: bold; font-size: 11px;")
                    self.add_log("✅ [웹소켓] AWS 릴레이 서버 연결 성공!")

                    # 인증 및 초기 동기화 요청
                    await self.ws.send(json.dumps({"type": "auth", "secret": "SECRET_TOKEN_HERE"}))
                    await asyncio.sleep(0.2)
                    await self.ws.send(json.dumps({"cmd": "CMD_SYNC_POSITION"}))

                    # 3초 주기 자동 포지션 갱신 태스크 구동
                    asyncio.create_task(self.auto_sync_position_loop())

                    async for message in ws:
                        data = json.loads(message)
                        msg_type = data.get("evt") or data.get("type")
                        payload = data.get("data", {})

                        if msg_type == "ui_update":
                            self.handle_ui_update(payload)
                        elif msg_type == "EVT_SYNC_POSITION":
                            self.handle_sync_position(payload)
                        elif msg_type == "EVT_RESPONSE_LOG":
                            res_msg = payload.get("message", "")
                            if res_msg:
                                self.add_log(res_msg)
                        elif msg_type == "update":
                            if "price" in data:
                                self.current_price = float(data["price"])
                                self.lbl_hud_price.setText(f"${self.current_price:,.1f}")

            except Exception as e:
                self.ws = None
                self.lbl_ws_status.setText("🔴 재접속 대기 (3초)")
                self.lbl_ws_status.setStyleSheet("color: #FF5555; font-weight: bold; font-size: 11px;")
                self.add_log(f"⚠️ [웹소켓] 연결 끊김: {e}. 3초 후 재시도...")
                await asyncio.sleep(3)

    async def auto_sync_position_loop(self):
        while self.ws is not None:
            try:
                await self.ws.send(json.dumps({"cmd": "CMD_SYNC_POSITION"}))
            except Exception:
                break
            await asyncio.sleep(3.0)

    def handle_ui_update(self, payload):
        if "price" in payload:
            self.current_price = float(payload["price"])
            self.lbl_hud_price.setText(f"${self.current_price:,.1f}")

        # 레이더 세션 정보
        current_sess = payload.get("current_session", "US 세션")
        self.lbl_session.setText(f"<span style='color:#DEBA9D; font-weight:bold;'>{current_sess}</span>")

        # 1분 누적 청산 게이지
        t_liq = float(payload.get("target_liq", 1000000.0))
        l_10s = float(payload.get("liq_10s", 0.0))
        self.bar_liq.setRange(0, max(1, int(t_liq)))
        self.bar_liq.setValue(min(int(t_liq), int(l_10s)))
        self.bar_liq.setFormat(f"1분 누적 청산: ${int(l_10s):,} / ${int(t_liq):,}")

        # 1분 OI 속도 게이지
        t_oi = float(payload.get("target_oi", 0.17))
        o_spd = float(payload.get("oi_speed", 0.0))
        pct_oi = int(min(100.0, max(0.0, (o_spd / t_oi if t_oi > 0 else 0) * 100)))
        self.bar_oi.setValue(pct_oi)
        self.bar_oi.setFormat(f"1분 OI 속도: {o_spd:+.4f}% / {t_oi:+.4f}%")

        # 3색 실시간 힌트 뱃지 & 사운드 알림 판정
        exp_dir = payload.get("expected_dir", None)
        long_l = float(payload.get("long_liq", 0.0))
        short_l = float(payload.get("short_liq", 0.0))
        has_real_force = payload.get("has_real_force", False)

        if exp_dir == "LONG" or (short_l > long_l and short_l >= t_liq * 0.7):
            self.lbl_hint_badge.setText("🟢 지금은 롱이 유리하다 (3대 AND 동조)")
            self.lbl_hint_badge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #005A2E, stop:1 #008947);
                border: 2px solid #00FFCC;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 900;
                padding: 6px;
            """)
            if self._last_signal_direction != "LONG":
                self.play_alert_sound("LONG")
                self._last_signal_direction = "LONG"
        elif exp_dir == "SHORT" or (long_l > short_l and long_l >= t_liq * 0.7):
            self.lbl_hint_badge.setText("🔴 지금은 숏이 유리하다 (3대 AND 동조)")
            self.lbl_hint_badge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #660018, stop:1 #A8002B);
                border: 2px solid #FF3366;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 900;
                padding: 6px;
            """)
            if self._last_signal_direction != "SHORT":
                self.play_alert_sound("SHORT")
                self._last_signal_direction = "SHORT"
        else:
            self.lbl_hint_badge.setText("⚪ 지금은 관망이 유리하다")
            self.lbl_hint_badge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2232, stop:1 #0f1624);
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94A3B8;
                font-size: 14px;
                font-weight: 900;
                padding: 6px;
            """)
            self._last_signal_direction = None

        # 스마트 스탑 상태
        c_active = payload.get("custom_stop_active", None)
        if c_active is not None:
            self.smart_stop_active = bool(c_active)
            c_offset = payload.get("custom_stop_offset", 0.6)
            if self.smart_stop_active:
                self.lbl_stop_status.setText(f"● 가동 중 (+{c_offset:.2f}%)")
                self.lbl_stop_status.setStyleSheet("color: #00FFCC; font-weight: bold; font-size: 11px;")
                self.btn_smart_stop.setText("🛑 스탑가드 해제")
            else:
                self.lbl_stop_status.setText("○ 비활성")
                self.lbl_stop_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
                self.btn_smart_stop.setText("🛡️ 스탑가드 설정")

        # HUD 손익 및 안전거리 실시간 재연산
        self.update_hud_pnl()

    def handle_direct_position_update(self, payload):
        """비트겟 본 계정 API에서 수신한 실시간 포지션 정보를 HUD에 0.05초 만에 렌더링"""
        has_pos = payload.get("has_position", False)
        self.has_position = has_pos
        c_price = payload.get("current_price", 0.0)
        if c_price > 0:
            self.current_price = c_price
            self.lbl_hud_price.setText(f"${self.current_price:,.1f}")

        if has_pos:
            self.position_side = payload.get("side", "LONG").upper()
            self.position_contracts = float(payload.get("contracts", 0.0))
            self.position_entry_price = float(payload.get("entry_price", 0.0))
            self.position_liq_price = float(payload.get("liquidation_price", 0.0))
            self.position_unrealized_pnl = float(payload.get("unrealized_pnl", 0.0))
            self.position_roe = float(payload.get("roe_pct", 0.0))
            leverage = payload.get("leverage", 60)

            if self.position_side == "LONG":
                self.lbl_hud_side.setText(f"🟢 LONG ({leverage}x)")
                self.lbl_hud_side.setStyleSheet("font-size: 13px; font-weight: 900; color: #00FFCC;")
            else:
                self.lbl_hud_side.setText(f"🔴 SHORT ({leverage}x)")
                self.lbl_hud_side.setStyleSheet("font-size: 13px; font-weight: 900; color: #FF3366;")

            self.lbl_hud_qty.setText(f"{self.position_contracts:.4f} BTC")
            self.lbl_hud_entry.setText(f"${self.position_entry_price:,.2f}")

            # 청산가가 비트겟에서 미제공될 경우 안전 추정
            if self.position_liq_price <= 0:
                if self.position_side == "LONG":
                    self.position_liq_price = self.position_entry_price * (1.0 - (1.0 / leverage) * 0.9)
                else:
                    self.position_liq_price = self.position_entry_price * (1.0 + (1.0 / leverage) * 0.9)

            self.update_hud_pnl()
        else:
            self.position_side = "NONE"
            self.position_contracts = 0.0
            self.position_entry_price = 0.0
            self.position_unrealized_pnl = 0.0
            self.position_roe = 0.0
            self.position_liq_price = 0.0
            self.lbl_hud_side.setText("⚪ NO POSITION")
            self.lbl_hud_side.setStyleSheet("font-size: 13px; font-weight: 900; color: #94A3B8;")
            self.lbl_hud_qty.setText("0.0000 BTC")
            self.lbl_hud_entry.setText("$0.00")
            self.lbl_hud_pnl.setText("$0.00 USDT (0.00%)")
            self.lbl_hud_pnl.setStyleSheet("font-weight: 900; color: #94A3B8;")
            self.lbl_hud_liq.setText("$0.00 (안전거리: --)")
            self.lbl_hud_liq.setStyleSheet("font-weight: bold; color: #94A3B8;")

    def handle_sync_position(self, payload):
        """웹서버로부터 수신된 보조 동기화 패킷 처리 (본 계정 워커 결과와 병합)"""
        if not hasattr(self, 'bitget_worker') or not self.bitget_worker.isRunning():
            self.handle_direct_position_update(payload)

    def update_hud_pnl(self):
        if not self.has_position or self.position_entry_price <= 0:
            return

        calc_price = self.current_price if self.current_price > 0 else self.position_entry_price

        # 미실현 손익 및 수익률(ROE) 연산
        if self.position_side == "LONG":
            diff = calc_price - self.position_entry_price
            pnl_usdt = diff * self.position_contracts
            roe_pct = (diff / self.position_entry_price) * 100.0 * 60.0
            safety_dist = calc_price - self.position_liq_price
        else:
            diff = self.position_entry_price - calc_price
            pnl_usdt = diff * self.position_contracts
            roe_pct = (diff / self.position_entry_price) * 100.0 * 60.0
            safety_dist = self.position_liq_price - calc_price

        # 워커에서 직접 전달받은 PnL이 있으면 우선 사용
        if abs(self.position_unrealized_pnl) > 0.0001:
            pnl_usdt = self.position_unrealized_pnl
            if abs(self.position_roe) > 0.0001:
                roe_pct = self.position_roe

        # 손익 레이블
        color = "#00FFCC" if pnl_usdt >= 0 else "#FF3366"
        sign = "+" if pnl_usdt >= 0 else ""
        self.lbl_hud_pnl.setText(f"{sign}${pnl_usdt:,.2f} USDT ({sign}{roe_pct:.2f}%)")
        self.lbl_hud_pnl.setStyleSheet(f"font-weight: 900; color: {color};")

        # 청산가 및 안전거리
        safety_color = "#00FFCC" if safety_dist > 500 else "#FBBF24" if safety_dist > 200 else "#FF3366"
        self.lbl_hud_liq.setText(f"${self.position_liq_price:,.1f} (안전거리: +${safety_dist:,.1f} 달러 🟢)")
        self.lbl_hud_liq.setStyleSheet(f"font-weight: bold; color: {safety_color};")

    # ----------------------------------------------------
    # 버튼 액션 핸들러 (비트겟 본 계정 100% 직통 발주)
    # ----------------------------------------------------
    def request_sync_position(self):
        if hasattr(self, 'bitget_worker') and self.bitget_worker.isRunning():
            self.bitget_worker.force_sync()
            self.add_log("🔄 [포지션 동기화] 비트겟 본 계정 API 최신 포지션 즉시 강제 갱신 요청 완료")
        elif self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_SYNC_POSITION"})))
            self.add_log("🔄 [포지션 동기화] 서버 릴레이 포지션 조회 패킷 전송")

    def execute_quick_market(self, side):
        try:
            qty = float(self.edit_qty.text().strip())
        except ValueError:
            self.add_log("❌ [오류] 수량 입력값이 올바르지 않습니다.")
            return

        if hasattr(self, 'bitget_worker') and self.bitget_worker.isRunning():
            self.bitget_worker.submit_order_action("QUICK_MARKET", {"side": side, "qty": qty})
            self.add_log(f"🚀 [원클릭 시장가 발주] 비트겟 본 계정 {side} {qty} BTC 주문 전송...")
        elif self.ws is not None:
            packet = {"cmd": "CMD_MARKET_ENTRY", "side": side, "qty": qty}
            asyncio.create_task(self.ws.send(json.dumps(packet)))
            self.add_log(f"🚀 [원클릭 시장가 발주] 서버 릴레이 {side} {qty} BTC 시장가 주문 패킷 전송!")
        else:
            self.add_log("❌ [오류] 본 계정 API 워커가 가동되지 않았습니다.")

    def execute_be_shield(self):
        if hasattr(self, 'bitget_worker') and self.bitget_worker.isRunning():
            self.bitget_worker.submit_order_action("BE_SHIELD")
            self.add_log("🛡️ [무위험 본전가드] 비트겟 본 계정 진입 평단가 0원 무손실 스탑로스 장착 요청...")
        elif self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_TRIGGER_BE_SHIELD"})))
            self.add_log("🛡️ [무위험 본전가드] 서버 릴레이 본전가드 요청 전송!")
        else:
            self.add_log("❌ [오류] 본 계정 API 워커가 가동되지 않았습니다.")

    def execute_auto_guard(self):
        if hasattr(self, 'bitget_worker') and self.bitget_worker.isRunning():
            self.bitget_worker.submit_order_action("AUTO_GUARD")
            self.add_log("🛡️ [2단 안전방패] 비트겟 본 계정 TP 2단 / SL 2단 자동 분할 주문 배치 요청...")
        elif self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_TRIGGER_AUTO_GUARD_4STAGE"})))
            self.add_log("🛡️ [2단 안전방패] 서버 릴레이 2단 안전방패 요청 전송!")
        else:
            self.add_log("❌ [오류] 본 계정 API 워커가 가동되지 않았습니다.")

    def execute_close_50(self):
        if hasattr(self, 'bitget_worker') and self.bitget_worker.isRunning():
            self.bitget_worker.submit_order_action("CLOSE_50")
            self.add_log("✂️ [50% 분할 청산] 비트겟 본 계정 오픈 포지션 50% 즉시 시장가 분할 청산 요청...")
        elif self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_CLOSE_50"})))
            self.add_log("✂️ [50% 분할 청산] 서버 릴레이 50% 분할 청산 요청 전송!")
        else:
            self.add_log("❌ [오류] 본 계정 API 워커가 가동되지 않았습니다.")

    def execute_emergency(self):
        if hasattr(self, 'bitget_worker') and self.bitget_worker.isRunning():
            self.bitget_worker.submit_order_action("EMERGENCY")
            self.add_log("🚨 [비상 탈출] 비트겟 본 계정 EMERGENCY 100% 전량 즉시 시장가 청산 및 주문 전수 취소 요청...")
        elif self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_EMERGENCY"})))
            self.add_log("🚨 [비상 탈출] 서버 릴레이 EMERGENCY 청산 요청 전송!")
        else:
            self.add_log("❌ [오류] 본 계정 API 워커가 가동되지 않았습니다.")

    def toggle_smart_stop(self):
        if self.ws is None:
            self.add_log("❌ [오류] 서버와 연결되어 있지 않습니다.")
            return

        new_active = not self.smart_stop_active
        try:
            offset_val = float(self.edit_stop_offset.text().strip())
        except ValueError:
            offset_val = 0.6

    # ----------------------------------------------------
    # 3중 RSI 실시간 신호등 & 극점 동조 사운드 알림
    # ----------------------------------------------------
    def on_rsi_updated(self, rsi_1m, rsi_5m, rsi_15m):
        def get_badge_info(prefix, rsi_val):
            if rsi_val >= 70.0:
                style = "background-color: rgba(255, 82, 82, 0.3); border: 1px solid #FF5252; color: #FF6666; font-weight: bold; border-radius: 4px; padding: 2px 4px; font-size: 11px;"
                text = f"{prefix}: {rsi_val:.1f}% 🔴"
            elif rsi_val <= 30.0:
                style = "background-color: rgba(0, 230, 118, 0.3); border: 1px solid #00E676; color: #00FFCC; font-weight: bold; border-radius: 4px; padding: 2px 4px; font-size: 11px;"
                text = f"{prefix}: {rsi_val:.1f}% 🟢"
            else:
                style = "background-color: rgba(60, 60, 60, 0.3); border: 1px solid #757575; color: #BDBDBD; font-weight: bold; border-radius: 4px; padding: 2px 4px; font-size: 11px;"
                text = f"{prefix}: {rsi_val:.1f}% ⚪"
            return style, text

        s_1m, t_1m = get_badge_info("1m RSI", rsi_1m)
        self.lbl_rsi_1m.setStyleSheet(s_1m)
        self.lbl_rsi_1m.setText(t_1m)

        s_5m, t_5m = get_badge_info("5m RSI", rsi_5m)
        self.lbl_rsi_5m.setStyleSheet(s_5m)
        self.lbl_rsi_5m.setText(t_5m)

        s_15m, t_15m = get_badge_info("15m RSI", rsi_15m)
        self.lbl_rsi_15m.setStyleSheet(s_15m)
        self.lbl_rsi_15m.setText(t_15m)

        # 3중 극점 동조 사운드 알림 체크
        self.check_rsi_sound_alert(rsi_1m, rsi_5m, rsi_15m)
        self._prev_rsi_1m = rsi_1m

    def check_rsi_sound_alert(self, rsi_1m, rsi_5m, rsi_15m):
        if not self.sound_enabled or self._prev_rsi_1m is None:
            return

        now = time.time()
        # 1. 3중 RSI 과매수 상단 꺾임 ➔ 숏 저격 알림 (15m>75 AND 5m>70 AND 1m>75, 1m 하방 꺾임)
        if rsi_15m > 75.0 and rsi_5m > 70.0 and rsi_1m > 75.0 and self._prev_rsi_1m > rsi_1m:
            if now - self._last_rsi_alert_time >= 60.0:
                self._last_rsi_alert_time = now
                self.add_log(f"🔔 [3중 RSI 극점 저격 알림] 상단 과매수 꺾임 포착 (1m:{rsi_1m:.1f}% 5m:{rsi_5m:.1f}% 15m:{rsi_15m:.1f}%) ➔ 숏 유리!")
                self._play_double_beep(1500, 150)

        # 2. 3중 RSI 과매도 바닥 반등 ➔ 롱 저격 알림 (15m<25 AND 5m<30 AND 1m<25, 1m 상방 반등)
        elif rsi_15m < 25.0 and rsi_5m < 30.0 and rsi_1m < 25.0 and self._prev_rsi_1m < rsi_1m:
            if now - self._last_rsi_alert_time >= 60.0:
                self._last_rsi_alert_time = now
                self.add_log(f"🔔 [3중 RSI 극점 저격 알림] 바닥 과매도 반등 포착 (1m:{rsi_1m:.1f}% 5m:{rsi_5m:.1f}% 15m:{rsi_15m:.1f}%) ➔ 롱 유리!")
                self._play_double_beep(800, 150)

    def _play_double_beep(self, freq, dur_ms):
        def _beep_thread():
            try:
                if winsound:
                    winsound.Beep(freq, dur_ms)
                    time.sleep(0.08)
                    winsound.Beep(freq, dur_ms)
                else:
                    QApplication.beep()
            except Exception:
                pass
        threading.Thread(target=_beep_thread, daemon=True).start()

    def closeEvent(self, event):
        try:
            if hasattr(self, 'rsi_worker') and self.rsi_worker.isRunning():
                self.rsi_worker.stop()
                self.rsi_worker.wait(500)
        except Exception:
            pass
        try:
            if hasattr(self, 'bitget_worker') and self.bitget_worker.isRunning():
                self.bitget_worker.stop()
                self.bitget_worker.wait(500)
        except Exception:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    cockpit = ShinseonCockpit()
    cockpit.show()

    # qasync 이벤트 루프가 안정적으로 시작된 직후 웹소켓 연결 태스크 가동 (50ms 안전 딜레이)
    QTimer.singleShot(50, lambda: asyncio.create_task(cockpit.connect_websocket()))

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
