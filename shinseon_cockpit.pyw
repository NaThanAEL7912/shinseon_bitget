# -*- coding: utf-8 -*-
"""
[神選 : SHINSEON] 국왕 폐하 전용 수동매매 초슬림 미니 콕핏 위젯 (Cockpit Widget V7.79)
창 크기: 가로 500px 초슬림 설계 (웹 브라우저 및 트레이딩뷰 차트 옆 밀착 배치용)
테마: 황실 다크 글래스 테마 (#0b0e14 배경, 골드/네온 액센트, 고대비 가독성)
"""

import sys
import os
import asyncio
import json
import time
import socket
import urllib.request
import ssl
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
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QBrush, QPainter
import websockets
from qasync import QEventLoop

# 1. 절대 이식성 상대 경로 추적
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VERSION = "V7.79"

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

        self.init_ui()
        self.load_config()

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

    def handle_sync_position(self, payload):
        has_pos = payload.get("has_position", False)
        self.has_position = has_pos

        if has_pos:
            self.position_side = payload.get("side", "LONG").upper()
            self.position_contracts = float(payload.get("contracts", 0.0))
            self.position_entry_price = float(payload.get("entry_price", 0.0))
            leverage = payload.get("leverage", 30)

            if self.position_side == "LONG":
                self.lbl_hud_side.setText(f"🟢 LONG ({leverage}x)")
                self.lbl_hud_side.setStyleSheet("font-size: 13px; font-weight: 900; color: #00FFCC;")
            else:
                self.lbl_hud_side.setText(f"🔴 SHORT ({leverage}x)")
                self.lbl_hud_side.setStyleSheet("font-size: 13px; font-weight: 900; color: #FF3366;")

            self.lbl_hud_qty.setText(f"{self.position_contracts:.4f} BTC")
            self.lbl_hud_entry.setText(f"${self.position_entry_price:,.2f}")

            # 강제 청산가 추정 (격리 30배 기준 또는 대략 96.7% 거리)
            if self.position_side == "LONG":
                self.position_liq_price = self.position_entry_price * (1.0 - (1.0 / leverage) * 0.9)
            else:
                self.position_liq_price = self.position_entry_price * (1.0 + (1.0 / leverage) * 0.9)

            self.update_hud_pnl()
        else:
            self.position_side = "NONE"
            self.position_contracts = 0.0
            self.position_entry_price = 0.0
            self.lbl_hud_side.setText("⚪ NO POSITION")
            self.lbl_hud_side.setStyleSheet("font-size: 13px; font-weight: 900; color: #94A3B8;")
            self.lbl_hud_qty.setText("0.0000 BTC")
            self.lbl_hud_entry.setText("$0.00")
            self.lbl_hud_pnl.setText("$0.00 USDT (0.00%)")
            self.lbl_hud_pnl.setStyleSheet("font-weight: 900; color: #94A3B8;")
            self.lbl_hud_liq.setText("$0.00 (안전거리: --)")
            self.lbl_hud_liq.setStyleSheet("font-weight: bold; color: #94A3B8;")

    def update_hud_pnl(self):
        if not self.has_position or self.position_entry_price <= 0 or self.current_price <= 0:
            return

        if self.position_side == "LONG":
            diff = self.current_price - self.position_entry_price
            pnl_usdt = diff * self.position_contracts
            roe_pct = (diff / self.position_entry_price) * 100.0 * 30.0 # 30배 기준
            safety_dist = self.current_price - self.position_liq_price
        else:
            diff = self.position_entry_price - self.current_price
            pnl_usdt = diff * self.position_contracts
            roe_pct = (diff / self.position_entry_price) * 100.0 * 30.0
            safety_dist = self.position_liq_price - self.current_price

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
    # 버튼 액션 핸들러
    # ----------------------------------------------------
    def request_sync_position(self):
        if self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_SYNC_POSITION"})))
            self.add_log("🔄 [포지션 동기화] 비트겟 최신 포지션 조회 패킷 전송")

    def execute_quick_market(self, side):
        try:
            qty = float(self.edit_qty.text().strip())
        except ValueError:
            self.add_log("❌ [오류] 수량 입력값이 올바르지 않습니다.")
            return

        if self.ws is not None:
            packet = {"cmd": "CMD_MARKET_ENTRY", "side": side, "qty": qty}
            asyncio.create_task(self.ws.send(json.dumps(packet)))
            self.add_log(f"🚀 [원클릭 시장가 발주] {side} {qty} BTC 시장가 주문 패킷 전송!")
        else:
            self.add_log("❌ [오류] 서버와 연결되어 있지 않습니다.")

    def execute_be_shield(self):
        if self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_TRIGGER_BE_SHIELD"})))
            self.add_log("🛡️ [무위험 본전가드] 진입 평단가 0원 무손실 스탑로스 장착 요청!")
        else:
            self.add_log("❌ [오류] 서버와 연결되어 있지 않습니다.")

    def execute_auto_guard(self):
        if self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_TRIGGER_AUTO_GUARD_4STAGE"})))
            self.add_log("🛡️ [2단 안전방패] TP 2단 / SL 2단 자동 분할 주문 배치 요청!")
        else:
            self.add_log("❌ [오류] 서버와 연결되어 있지 않습니다.")

    def execute_close_50(self):
        if self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_CLOSE_50"})))
            self.add_log("✂️ [50% 분할 청산] 오픈 포지션 50% 즉시 시장가 분할 청산 요청!")
        else:
            self.add_log("❌ [오류] 서버와 연결되어 있지 않습니다.")

    def execute_emergency(self):
        if self.ws is not None:
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_EMERGENCY"})))
            self.add_log("🚨 [비상 탈출] EMERGENCY 100% 전량 즉시 시장가 청산 및 주문 전수 취소!")
        else:
            self.add_log("❌ [오류] 서버와 연결되어 있지 않습니다.")

    def toggle_smart_stop(self):
        if self.ws is None:
            self.add_log("❌ [오류] 서버와 연결되어 있지 않습니다.")
            return

        new_active = not self.smart_stop_active
        try:
            offset_val = float(self.edit_stop_offset.text().strip())
        except ValueError:
            offset_val = 0.6

        packet = {
            "cmd": "CMD_SET_SMART_STOP",
            "active": new_active,
            "offset_val": offset_val,
            "ratio": 100.0
        }
        asyncio.create_task(self.ws.send(json.dumps(packet)))
        act_str = f"설정 (+{offset_val:.2f}%)" if new_active else "해제"
        self.add_log(f"🛡️ [스마트 스탑] {act_str} 명령 전송 완료")


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
