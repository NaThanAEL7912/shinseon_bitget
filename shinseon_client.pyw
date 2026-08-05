import sys
import os

# --- 크로미움 커널 디스크 직송 플러시 & 제3자 저장소 파티셔닝 차단 해제 ---
sys.argv.append("--disable-features=ThirdPartyStoragePartitioning")
sys.argv.append("--enable-aggressive-domstorage-flushing")
sys.argv.append("--allow-running-insecure-content")
import asyncio
import random
import logging
import time
import re
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QWidget, QLabel, QLineEdit, QTextEdit, QPlainTextEdit,
                             QGraphicsDropShadowEffect, QProgressBar, QCheckBox,
                             QScrollArea, QFrame, QDialog, QTabWidget, QGridLayout, QGroupBox)
from PySide6.QtCore import Qt, QPointF, QRectF, QUrl
from PySide6.QtGui import QPainter, QPicture, QColor, QFont, QBrush, QPen, QLinearGradient
from PySide6.QtWebEngineWidgets import QWebEngineView
import pyqtgraph as pg
from qasync import QEventLoop
import websockets
import json
import socket
import urllib.request
import re
import uuid
import csv
from io import StringIO

# --- 국내 통신사 바이낸스 DNS 차단 우회용 Google DoH(DNS-over-HTTPS) 터널링 패치 ---
import ssl

original_getaddrinfo = socket.getaddrinfo
dns_cache = {}

# Google DoH IP(8.8.8.8) 직접 조회를 위한 무검증 SSL 컨텍스트
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# aiohttp가 aiodns를 우회하여 socket.getaddrinfo를 강제 사용하도록 패치
try:
    aiohttp.connector.DefaultResolver = aiohttp.ThreadedResolver
except Exception:
    pass

def secure_doh_resolve(host):
    if not re.search(r'(?:binance|fapi\.binance|stream\.binance)\.com', host, re.IGNORECASE):
        return None
    if host in dns_cache:
        return dns_cache[host]
    try:
        # DNS 서버 불통 및 검열 우회를 위해 Google DNS IP(8.8.8.8)로 직접 질의
        url = f"https://8.8.8.8/resolve?name={host}&type=A"
        req = urllib.request.Request(url, headers={'Host': 'dns.google', 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.5, context=ssl_ctx) as r:
            data = json.loads(r.read().decode())
            answers = data.get("Answer", [])
            ips = []
            for ans in answers:
                if ans.get("type") == 1: # A record
                    ips.append(ans.get("data"))
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
# ------------------------------------------------------------------------------

# ==============================================================================
# [神選 : 신선 (신의 선택)] 프로젝트 신선 윈도우 대시보드 마스터 v2.0.0
# 디자인 콘셉트: Imperial Obsidian Halo (3D 메탈릭 & 네온 골드 헤일로 리치 에디션)
# 완전한 무설치 이식성 및 5단계 가드레일 시뮬레이션 엔진 포함
# ==============================================================================

# 1. 절대 이식성 상대 경로 추적 로직 (데스크탑-노트북 완벽 이관 구동 가능)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# GitHub 설정 (라이선스 동기화용)
GITHUB_OWNER = "NaThanAEL7912"
GITHUB_REPO = "shinseon_bitget"
GITHUB_BRANCH = "main"
LICENSE_URL = "https://raw.githubusercontent.com/NaThanAEL7912/shinseon_bitget/main/docs/license.json"

# 2. client_config.json 환경변수 수동 파싱 엔진 (dotenv 패키지 의존성 완전 제거)
def load_env_file():
    return {"SECRET_TOKEN": "YOUR_SECRET_TOKEN"}

env_vars = load_env_file()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ShinseonBot")


# ==============================================================================
# PyQtGraph 커스텀 캔들스틱 차트 아이템 정의 (피치 누드 골드 & 빈티지 테라코타 레드)
# ==============================================================================
class CandlestickItem(pg.GraphicsObject):
    """PyQtGraph 용 고성능 커스텀 캔들스틱 렌더링 클래스 (피치 골드 & 테라코타 레드 적용)"""
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # 형식: [(x, open, close, low, high), ...]
        self.picture = QPicture()
        self.generatePicture()

    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        # Velvet Precision / Imperial Obsidian 캔들 색상 대치
        up_pen = pg.mkPen(color='#E8B890', width=2.0)      # 상승 캔들 테두리 (피치 누드 골드)
        down_pen = pg.mkPen(color='#AC5A52', width=2.0)    # 하락 캔들 테두리 (빈티지 테라코타 레드)
        up_brush = pg.mkBrush(QColor(232, 184, 144, 40))   # 상승 캔들 채우기 (피치골드 반투명)
        down_brush = pg.mkBrush(QColor(172, 90, 82, 40))   # 하락 캔들 채우기 (테라코타 반투명)
        
        if len(self.data) > 1:
            w = (self.data[1][0] - self.data[0][0]) / 3.0
        else:
            w = 0.3
            
        for (t, open_p, close_p, low_p, high_p) in self.data:
            if open_p < close_p:
                p.setPen(up_pen)
                p.drawLine(QPointF(t, low_p), QPointF(t, high_p))
                p.setBrush(up_brush)
                p.drawRect(QRectF(t-w, open_p, w*2, close_p-open_p))
            else:
                p.setPen(down_pen)
                p.drawLine(QPointF(t, low_p), QPointF(t, high_p))
                p.setBrush(down_brush)
                p.drawRect(QRectF(t-w, open_p, w*2, close_p-open_p))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


def safe_int(val, default=0):
    try:
        if val is None:
            return default
        if isinstance(val, str):
            val = val.replace(",", "").strip()
        return int(float(val))
    except Exception:
        return default

def play_order_sound(sound_type="LONG", enabled=True):
    if not enabled:
        return
    def _sound_thread():
        try:
            import winsound
            if sound_type == "LONG":
                winsound.Beep(1000, 250)
                winsound.Beep(1600, 350)
            elif sound_type == "SHORT":
                winsound.Beep(1600, 250)
                winsound.Beep(1000, 350)
            elif sound_type == "CLEAR":
                winsound.Beep(800, 200)
                winsound.Beep(1200, 200)
                winsound.Beep(1800, 400)
            elif sound_type in ["ADD", "PYRAMID"]:
                winsound.Beep(1300, 250)
                winsound.Beep(1500, 250)
            else:
                winsound.Beep(1000, 300)
        except Exception:
            pass
    import threading
    threading.Thread(target=_sound_thread, daemon=True).start()

# ==============================================================================
# 양방향 프로그레스 바 클래스 (BidirectionalProgressBar)
# ==============================================================================
class BidirectionalProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_val = 0
        self.max_val = 100
        self.val = 0
        self.format_str = ""
        self.setFixedHeight(48)
        
    def setRange(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        self.update()
        
    def setValue(self, val):
        self.val = val
        self.update()
        
    def setFormat(self, format_str):
        self.format_str = format_str
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # 1. 배경색 #141312, 테두리 rgba(222, 186, 157, 0.25), border-radius 4px
        bg_brush = QBrush(QColor("#141312"))
        border_pen = QPen(QColor(222, 186, 157, int(255 * 0.25)))
        border_pen.setWidth(1)
        
        painter.setBrush(bg_brush)
        painter.setPen(border_pen)
        painter.drawRoundedRect(QRectF(rect), 4.0, 4.0)
        
        # 2. 정중앙(0%) 세로 놋쇠빛 점선 (rgba(222, 186, 157, 0.45))
        center_x = rect.width() / 2.0
        center_pen = QPen(QColor(222, 186, 157, int(255 * 0.45)))
        center_pen.setStyle(Qt.DashLine)
        center_pen.setWidth(1)
        
        # 3. 그라데이션 충전
        limit = abs(self.max_val) if self.max_val != 0 else 100
        ratio = float(self.val) / limit
        if ratio > 1.0:
            ratio = 1.0
        elif ratio < -1.0:
            ratio = -1.0
            
        fill_width = abs(ratio) * (rect.width() / 2.0)
        
        if ratio > 0:
            fill_rect = QRectF(center_x, 1.0, fill_width, rect.height() - 2.0)
            gradient = QLinearGradient(center_x, 0, center_x + fill_width, 0)
            gradient.setColorAt(0, QColor("#DEBA9D"))
            gradient.setColorAt(1, QColor("#52AC62"))
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRect(fill_rect)
        elif ratio < 0:
            fill_rect = QRectF(center_x - fill_width, 1.0, fill_width, rect.height() - 2.0)
            gradient = QLinearGradient(center_x, 0, center_x - fill_width, 0)
            gradient.setColorAt(0, QColor("#DEBA9D"))
            gradient.setColorAt(1, QColor("#AC5A52"))
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRect(fill_rect)
            
        painter.setPen(center_pen)
        painter.drawLine(QPointF(center_x, 1.0), QPointF(center_x, rect.height() - 1.0))
        
        # 4. 중앙에 Consolas 볼드체 9pt 텍스트 오버레이
        text_pen = QPen(QColor(255, 255, 255))
        painter.setPen(text_pen)
        font = QFont("Consolas", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.format_str)
        
        painter.end()


# ==============================================================================
# 메인 GUI 대시보드 클래스 (Imperial Obsidian Halo 입체 광택 QSS 적용)
# ==============================================================================
class ShinseonDashboard(QMainWindow):
    def __init__(self, bot_core):
        super().__init__()
        self.CURRENT_VERSION = "V4.25"  # [Phase 3] 서버-클라이언트 분리 및 CCXT 이관 (RPA 제거)
        self.auto_start = False
        self.sound_enabled = True
        self.price_alerts = []
        self.current_price = 0.0
        
        # 트레이딩뷰 차트 사용 지표/설정 영구 보존 캐시 디렉토리 바인딩
        try:
            from PySide6.QtWebEngineCore import QWebEngineProfile
            profile = QWebEngineProfile.defaultProfile()
            cache_dir = os.path.join(BASE_DIR, "docs", "web_cache")
            os.makedirs(cache_dir, exist_ok=True)
            profile.setPersistentStoragePath(cache_dir)
        except Exception:
            pass
        self.bot_core = bot_core
        self.bot_core.dashboard = self
        if self.bot_core and getattr(self.bot_core, "v35_engine", None):
            self.bot_core.v35_engine.is_snipe_active = False
        self.chart_data = []
        self.last_signal_text = ""
        
        # 텔레그램 알림 및 원격 제어 기본 변수 선언 (개발계획서_178)
        self.telegram_enabled = False
        self.telegram_token = ""
        self.telegram_chat_id = ""
        self.last_balance = 0.0
        self.last_pnl_usdt = 0.0
        self.last_price = 0.0
        self.last_current_session = "로딩 중"
        self.last_liq_1m = 0.0
        self.last_oi_speed = 0.0
        
        # 비동기 로그 작성 대기 큐 및 데몬 기동 (개발계획서_171)
        self.log_queue = asyncio.Queue()
        
        # 세션별 임계치 및 트레이딩 핵심 설정 기본값 정의 (개발계획서_176)
        self.session_thresholds = {
            "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
            "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
            "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
            "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3},
            "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
            "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
            "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
            "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3}
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
        self.pyramiding_enabled = True
        self.pyramiding_ratio = 30.0
        self.leverage_level = 20
        self.betting_ratio = 400.0
        self.split_entry_1_ratio = 250.0   # 1차 매수 비중 (%)
        self.split_entry_2_ratio = 100.0   # 2차 매수 비중 (%)
        self.split_entry_2_trigger_pct = -0.3 # 2차 진입 하락폭 (%)
        self.split_entry_3_ratio = 50.0    # 3차 매수 비중 (%)
        self.split_entry_3_trigger_pct = -0.6 # 3차 진입 하락폭 (%)
        self.split_cooldown_seconds = 900.0 # 추가 매수 후 진입 제한 시간 (초)
        self.cooldown_seconds = 60.0       # 손절 후 진입 제한 시간 (초)
        self.profit_cooldown_seconds = 15.0 # 익절 후 진입 제한 시간 (초)
        self.chart_loaded = False          # [수정] 차트 및 엔진 백그라운드 중복 기동 방지 플래그 (개발계획서_188_38)

        self.half_exit_enabled = True
        self.half_exit_trigger_pct = 0.6
        self.half_exit_close_ratio = 50.0
        self.entry_sl_guard_pct = 0.0
        
        self.init_ui()
        self.generate_initial_candles()
        self.init_audio()
        
        # 설정 파일 자동 로딩 및 신호 연결 (개발계획서_173)
        self.load_shinseon_config()
        self.chk_manual_threshold.stateChanged.connect(self.save_shinseon_config)
        self.edit_target_liq.textChanged.connect(self.save_shinseon_config)
        self.edit_target_oi.textChanged.connect(self.save_shinseon_config)
        self.edit_target_slippage.textChanged.connect(self.save_shinseon_config)
        
        # 부팅 시 3대 요소 자동 동기화 시퀀스 트리거 (0.1초 뒤 비동기 가동)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: asyncio.create_task(self.run_startup_sync_sequence()))
        
    def init_ui(self):
        self.setWindowTitle(f"[神選 : 신선 (신의 선택)] 마스터 대시보드 {self.CURRENT_VERSION}")
        self.setMinimumSize(1200, 750)
        self.resize(1350, 820)
        
        # 3D 스큐어모픽 질감 및 웜 코코아 & 샌드 골드 QSS 레이아웃
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0A0909; /* Level 0: 딥 코코아 블랙 */
            }
            QWidget {
                background-color: #0A0909;
                color: #F5EFEB; /* Base Text: 소프트 크림 화이트 */
                font-family: 'Malgun Gothic Semilight', 'Segoe UI Semibold', 'Segoe UI', 'Malgun Gothic', sans-serif;
                letter-spacing: -0.5px; /* 한글 자간을 미세하게 조여 촌스러움 격살 */
            }
            QLabel {
                font-size: 12px;
                color: #D3C4BA; /* Secondary Text: 샴페인 크림 베이지 */
                font-weight: 500;
                letter-spacing: -0.3px;
            }
            QTextEdit {
                background-color: #060505;
                border: 1px solid rgba(222, 186, 157, 0.12); /* 은은한 놋쇠 보더 */
                border-radius: 6px;
                color: #DEBA9D; /* 샌드 골드 텍스트 로그 */
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 10px;
                letter-spacing: 0px; /* 숫자 로그는 기본 자간 유지 */
            }
            /* 입력 필드: 움푹 파인 3D 안쪽 핏감을 주는 언더라인 스타일 */
            QLineEdit {
                background-color: transparent;
                border: none;
                border-bottom: 1.5px solid #3E3733; /* 다크 초콜릿 샌드 보더 */
                color: #FFFFFF;
                padding: 4px;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 0.5px; /* 코딩 숫자는 자간을 벌림 */
            }
            QLineEdit:focus {
                border-bottom: 2px solid #DEBA9D; /* 포커스 시 샌드 골드로 발광 */
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        
        # ----------------------------------------------------------------------
        # 최상단: 타이틀바 및 한자 현판 영역
        # ----------------------------------------------------------------------
        title_layout = QHBoxLayout()
        
        # 기계식 세리프 서체의 느낌을 주기 위해 Georgia / Times New Roman 바인딩
        self.lbl_brand = QLabel(
            "<span style='color: #DEBA9D; font-weight: bold; font-size: 20px; font-family: \"Georgia\", serif;'>神選 [SHINSEON]</span> "
            "<span style='font-size: 16px; font-weight: bold; color: #F5EFEB; font-family: \"Segoe UI\";'>- 신의 선택 마스터 터미널</span> "
            f"<span style='font-size: 11px; font-weight: bold; color: #C5A07A; border: 1px solid rgba(222, 186, 157, 0.35); border-radius: 3px; padding: 2px 6px; margin-left: 8px; vertical-align: middle;'>{self.CURRENT_VERSION}</span>"
        )
        lbl_status = QLabel("구동 상태: <span style='color: #DEBA9D; font-weight: bold;'>● 바이낸스 API 활성화</span>")
        lbl_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        title_layout.addWidget(self.lbl_brand)
        title_layout.addStretch()
        title_layout.addWidget(lbl_status)
        main_layout.addLayout(title_layout)
        
        # 3분할 패널 배치
        panel_layout = QHBoxLayout()
        panel_layout.setSpacing(18)
        
        # 3D 더블 보더 질감 QSS (차콜 블랙 #141312 바탕, 은은한 황동 보더선 및 6px 모서리)
        # 아이디 선택자(#)를 사용하여 지정된 4대 외곽 프레임 박스에만 골드 테두리를 입힘 (자식 겹침 보더 방지)
        panel_qss = """
            #left_panel, #center_panel, #log_panel, #right_panel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #171514, stop:1 #0F0E0E); /* 3D 입체 그라데이션 */
                border: 1px solid rgba(222, 186, 157, 0.15); /* 놋쇠 프레임 느낌 */
                border-radius: 6px;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
        """
        
        # ----------------------------------------------------------------------
        # (1) 우측 대통합 패널: 모든 설정/제어 기어 통합 적재
        # ----------------------------------------------------------------------
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(10)
        right_widget = QWidget()
        right_widget.setObjectName("right_panel")
        right_widget.setStyleSheet(panel_qss)
        right_widget.setLayout(right_layout)
        
        # 헤더 가로 레이아웃 구성하여 우측 끝에 ⚙ 버튼 장착
        header_layout = QHBoxLayout()
        header_label = QLabel("<b style='color:#FFFFFF; font-size: 13px;'>■ [新鮮] 자본 배치 및 설정</b>")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.btn_session_config = QPushButton("⚙", right_widget)
        self.btn_session_config.setToolTip("세션 및 트레이딩 핵심 설정")
        self.btn_session_config.setCursor(Qt.PointingHandCursor)
        self.btn_session_config.setFixedSize(32, 28)
        self.btn_session_config.setStyleSheet("""
            QPushButton {
                background: rgba(222, 186, 157, 0.15);
                border: 1px solid rgba(222, 186, 157, 0.4);
                border-radius: 4px;
                color: #DEBA9D;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(222, 186, 157, 0.35);
                color: #FFFFFF;
                border: 1px solid #DEBA9D;
            }
            QPushButton:pressed {
                background: #DEBA9D;
                color: #0F0E0E;
            }
        """)
        self.btn_session_config.clicked.connect(self.show_session_config_dialog)
        header_layout.addWidget(self.btn_session_config)
        right_layout.addLayout(header_layout)
        
        self.lbl_capital_display = QLabel("총 가용 자본금: $0.00 (실시간 동기화 대기)")
        self.lbl_capital_display.setStyleSheet("font-size: 13px; color: #DEBA9D; font-weight: bold; font-family: 'Consolas'; margin-top: 4px; margin-bottom: 4px;")
        right_layout.addWidget(self.lbl_capital_display)
        
        # 실전 계좌 잔고 동기화 버튼 (부모를 right_widget으로 변경)
        self.btn_sync_balance = QPushButton("🔄 실전 계좌 잔고 동기화", right_widget)
        self.btn_sync_balance.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DEBA9D, stop:1 #C5A07A);
                color: #0F0E0E;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #DEBA9D);
            }
        """)
        self.btn_sync_balance.clicked.connect(self.sync_account_balances)
        right_layout.addWidget(self.btn_sync_balance)
        

        
        # v3.5 오더플로우 레이더 감시 정보 패널 (상단 이관 완료 및 게이지 바 장착) (부모를 right_widget으로 변경)
        self.lbl_radar_title = QLabel("<br><b style='color:#FFFFFF; font-size: 13px;'>■ [雷達] 실시간 오더플로우 레이더</b>", right_widget)
        right_layout.addWidget(self.lbl_radar_title)
        
        # --- 임계치 수동 설정 제어반 (개발계획서_145) ---
        self.manual_panel = QWidget(right_widget)
        manual_layout = QHBoxLayout(self.manual_panel)
        manual_layout.setContentsMargins(0, 5, 0, 5) # 레이아웃 마진을 0, 5, 0, 5로 변경하여 게이지바 정렬선과 일치

        manual_layout.setSpacing(10)                  # 항목 간 간격 10px로 확대
        
        self.chk_manual_threshold = QCheckBox("수동 임계치", self.manual_panel)
        self.chk_manual_threshold.setChecked(False)
        self.chk_manual_threshold.setStyleSheet("""
            QCheckBox {
                color: #DEBA9D;
                font-weight: bold;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid rgba(222, 186, 157, 0.5);
                background-color: #141312;
                border-radius: 3px;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #DEBA9D;
            }
            QCheckBox::indicator:checked {
                background-color: #DEBA9D;
                border: 1px solid #DEBA9D;
            }
        """)
        manual_layout.addSpacing(10)
        manual_layout.addWidget(self.chk_manual_threshold)
        manual_layout.addStretch()
        
        self.edit_target_liq = QLineEdit(self.manual_panel)
        self.edit_target_liq.setPlaceholderText("청산 ($)")
        self.edit_target_liq.setText("2,500,000")
        self.edit_target_liq.setStyleSheet("""
            QLineEdit {
                background-color: #141312;
                border: 1px solid rgba(222, 186, 157, 0.3);
                color: #F5EFEB;
                font-family: 'Consolas';
                font-size: 11px;
                padding: 4px;
                border-radius: 3px;
                max-width: 90px;
            }
            QLineEdit:focus {
                border: 1px solid #DEBA9D;
            }
            QLineEdit:disabled {
                color: #FFFFFF;
                background-color: #1A1817;
                border: 1px solid rgba(222, 186, 157, 0.15);
            }
        """)
        manual_layout.addWidget(self.edit_target_liq)
        
        self.edit_target_oi = QLineEdit(self.manual_panel)
        self.edit_target_oi.setPlaceholderText("OI (%)")
        self.edit_target_oi.setText("0.12")
        self.edit_target_oi.setStyleSheet("""
            QLineEdit {
                background-color: #141312;
                border: 1px solid rgba(222, 186, 157, 0.3);
                color: #F5EFEB;
                font-family: 'Consolas';
                font-size: 11px;
                padding: 4px;
                border-radius: 3px;
                max-width: 60px;
            }
            QLineEdit:focus {
                border: 1px solid #DEBA9D;
            }
            QLineEdit:disabled {
                color: #FFFFFF;
                background-color: #1A1817;
                border: 1px solid rgba(222, 186, 157, 0.15);
            }
        """)
        manual_layout.addWidget(self.edit_target_oi)
        
        self.lbl_target_slippage = QLabel("슬리피지 (%)")
        self.lbl_target_slippage.setStyleSheet("color: #DEBA9D; font-weight: bold; font-size: 11px;")
        self.edit_target_slippage = QLineEdit("0.15")
        self.edit_target_slippage.setFixedWidth(50)
        self.edit_target_slippage.setStyleSheet("""
            QLineEdit {
                background-color: #141312;
                border: 1px solid rgba(222, 186, 157, 0.3);
                color: #F5EFEB;
                font-family: 'Consolas';
                font-size: 11px;
                padding: 3px;
                border-radius: 3px;
            }
            QLineEdit:disabled {
                color: #FFFFFF;
                background-color: #1A1817;
                border: 1px solid rgba(222, 186, 157, 0.15);
            }
        """)
        manual_layout.addWidget(self.lbl_target_slippage)
        manual_layout.addWidget(self.edit_target_slippage)
        
        self.chk_manual_threshold.stateChanged.connect(self.toggle_manual_threshold_inputs)
        self.toggle_manual_threshold_inputs()
        
        manual_layout.addSpacing(10)
        
        right_layout.addWidget(self.manual_panel)
        self.manual_panel.hide()
        
        self.bar_liq = QProgressBar()
        self.bar_liq.setTextVisible(True)
        self.bar_liq.setFormat("1분 누적 청산: $0 / $2.0M")
        self.bar_liq.setRange(0, 2000000)
        self.bar_liq.setValue(0)
        self.bar_liq.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(222, 186, 157, 0.25);
                border-radius: 4px;
                background-color: #141312;
                text-align: center;
                color: #F5EFEB;
                font-family: 'Consolas';
                font-size: 12px;
                font-weight: bold;
                height: 48px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DEBA9D, stop:1 #AC5A52);
                border-radius: 3px;
            }
        """)
        right_layout.addWidget(self.bar_liq)
        
        self.bar_oi = BidirectionalProgressBar(right_widget)
        self.bar_oi.setFormat("1분 OI 속도: +0.00% (임계: +1.00%)")
        self.bar_oi.setRange(0.0, 1.0)
        self.bar_oi.setValue(0.0)
        right_layout.addWidget(self.bar_oi)
        
        self.lbl_hint = QLabel("[ 타점 포착 대기 중 ]")
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        self.lbl_hint.setFixedHeight(24)
        self.lbl_hint.setStyleSheet("""
            QLabel {
                background-color: #141312;
                border: 1px solid rgba(222, 186, 157, 0.25);
                border-radius: 4px;
                color: #7B736D;
                font-family: 'Consolas';
                font-size: 12px;
                font-weight: bold;
            }
        """)
        right_layout.addWidget(self.lbl_hint)
        

        
        self.lbl_ping_ms = QLabel("패킷 레이턴시: 0.0ms (상시 모니터링)")
        self.lbl_ping_ms.setStyleSheet("font-size: 11px; color: #D3C4BA; font-family: 'Consolas';")
        right_layout.addWidget(self.lbl_ping_ms)
        
        self.lbl_poison_walls = QLabel("독약 방어벽: [정상 가동 중]")
        self.lbl_poison_walls.setStyleSheet("font-size: 11px; color: #C5A07A; font-weight: bold;")
        right_layout.addWidget(self.lbl_poison_walls)
        
        # 포지션 동기화 버튼 (부모를 right_widget으로 변경)
        self.btn_position_sync = QPushButton("🔄 포지션 동기화", right_widget)
        self.btn_position_sync.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DEBA9D, stop:1 #C5A07A);
                color: #0F0E0E;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #DEBA9D);
            }
        """)
        self.btn_position_sync.clicked.connect(self.trigger_position_sync)
        right_layout.addWidget(self.btn_position_sync)
        
        self.lbl_guardrail = QLabel("진입/청산 상태:\n[100% 현금 대기 중]")
        self.lbl_guardrail.setStyleSheet("font-size: 12px; color: #DEBA9D; font-weight: bold; line-height: 1.4;")
        right_layout.addWidget(self.lbl_guardrail)
        self.lbl_position_status = self.lbl_guardrail
        
        # ⚡ 레이턴시 실측 기어 및 결과 라벨 이식 (부모를 right_widget으로 변경)
        self.lbl_latency_gear_title = QLabel("<br><b style='color:#FFFFFF; font-size: 11px;'>■ [雷達] 레이턴시 실측 기어</b>", right_widget)
        right_layout.addWidget(self.lbl_latency_gear_title)
        
        # 레이턴시 실측 버튼 (부모를 right_widget으로 변경)
        self.btn_latency_test = QPushButton("⚡ 레이턴시 실측", right_widget)
        self.btn_latency_test.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DEBA9D, stop:1 #C5A07A);
                color: #0F0E0E;
                font-weight: bold;
                font-size: 11px;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #DEBA9D);
            }
        """)
        self.btn_latency_test.clicked.connect(self.trigger_latency_test)
        right_layout.addWidget(self.btn_latency_test)
        
        self.lbl_latency_result = QLabel("실측 결과: 대기 중")
        self.lbl_latency_result.setStyleSheet("font-size: 11px; color: #DEBA9D; font-family: 'Consolas'; font-weight: bold;")
        right_layout.addWidget(self.lbl_latency_result)
        
        self.lbl_auto_latency = QLabel("자동 감시: 대기 중")
        self.lbl_auto_latency.setStyleSheet("font-size: 11px; color: #C5A07A; font-family: 'Consolas'; font-weight: bold;")
        right_layout.addWidget(self.lbl_auto_latency)
        
        self.lbl_latency_gear_title.hide()
        self.btn_latency_test.hide()
        self.lbl_latency_result.hide()
        self.lbl_auto_latency.hide()
        
        # ----------------------------------------------------------------------
        # (2) 중앙 패널: 실시간 시세 및 트레이딩뷰 차트 (텍스트 전면 격살 및 꽉 차게 팽창)
        # ----------------------------------------------------------------------
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0) # 사방 여백 제거
        center_layout.setSpacing(0)
        
        center_widget = QWidget()
        center_widget.setObjectName("center_panel")
        center_widget.setStyleSheet(panel_qss)
        center_widget.setLayout(center_layout)
        
        # 참조 무결성을 위해 가격/시그널 위젯은 백엔드 메모리에 가상 생성 후 은폐 처리
        self.lbl_price = QLabel("BTC/USDT 실시간 가격: 68,500.0 USDT")
        self.lbl_price.hide()
        self.lbl_signal = QLabel("神先 시그널: [대기 중]")
        self.lbl_signal.hide()
        self.lbl_latency = QLabel("迅先 레이턴시: 8ms (정상)")
        self.lbl_latency.hide()
        
        # 트레이딩뷰 실시간 선물 차트 웹뷰 위젯 장착 (영구 디스크 프로필 QWebEnginePage 도킹 설계)
        try:
            from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
            cache_dir = os.path.join(BASE_DIR, "docs", "web_cache")
            os.makedirs(cache_dir, exist_ok=True)
            self.web_profile = QWebEngineProfile("shinseon_persistent_v2", self)
            self.web_profile.setPersistentStoragePath(cache_dir)
            self.web_profile.setCachePath(cache_dir)
            self.web_profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
            self.web_page = QWebEnginePage(self.web_profile, self)
            self.chart_view = QWebEngineView()
            self.chart_view.setPage(self.web_page)
        except Exception as e:
            logger.error(f"웹뷰 프로필 바인딩 오류: {e}")
            self.chart_view = QWebEngineView()
            
        self.chart_view.setStyleSheet("background-color: #141312; border: none; border-radius: 6px;")
        center_layout.addWidget(self.chart_view)
        
        # ----------------------------------------------------------------------
        # (3) 우측 대통합 하단 제어부: 봇 가동 제어 및 가드레일 추적
        # ----------------------------------------------------------------------
        right_layout.addWidget(QLabel("<br><b style='color:#FFFFFF; font-size: 13px;'>■ [信線] 봇 상태 및 가드레일 제어</b>"))
        
        # START 버튼: 3D 기계식 물리 스위치 (부모를 right_widget으로 변경)
        # 자동 봇 시작 버튼: 3D 기계식 물리 스위치 (부모를 right_widget으로 변경)
        self.btn_start = QPushButton("▶ 자동 봇 시작", right_widget)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DEBA9D, stop:1 #C5A07A); /* 3D 그라데이션 */
                color: #0F0E0E; /* 차콜 브라운 글씨 */
                font-weight: bold; 
                font-size: 13px; 
                padding: 11px; 
                border-radius: 4px;
                border: 1px solid #A88869;
                border-top: 1.5px solid rgba(255, 255, 255, 0.35); /* 상단 반사 베벨 */
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #DEBA9D);
            }
        """)
        self.btn_start.clicked.connect(self.start_bot)
        right_layout.addWidget(self.btn_start)
        
        # [2행] ⚡ 수동 봇 시작: 딥 머드 브라운 gradient
        self.btn_manual_start = QPushButton("⚡ 수동 봇 시작", right_widget)
        self.btn_manual_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8C7355, stop:1 #594733);
                color: #F5EFEB;
                font-weight: bold; 
                font-size: 13px; 
                padding: 11px; 
                border-radius: 4px;
                border: 1px solid #735D43;
                border-top: 1.5px solid rgba(255, 255, 255, 0.25);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A18663, stop:1 #8C7355);
            }
        """)
        self.btn_manual_start.clicked.connect(self.manual_start_bot)
        right_layout.addWidget(self.btn_manual_start)
        self.btn_manual_start.hide()
        
        # [3행] 🚨 비상 탈출 버튼: 부모를 right_widget으로 변경
        self.btn_emergency = QPushButton("🚨 비상 탈출 (EMERGENCY)", right_widget)
        self.btn_emergency.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AC5A52, stop:1 #732E27);
                color: #F5EFEB; 
                font-weight: bold; 
                font-size: 13px; 
                padding: 11px; 
                border-radius: 4px;
                border: 2px solid #C5A07A; /* 황동 베젤 */
                border-top: 1.5px solid rgba(255, 255, 255, 0.25);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #BD6D65, stop:1 #AC5A52);
            }
        """)
        self.btn_emergency.clicked.connect(self.emergency_close)
        
        # 웜 샌드 골드 네온 링(Halo) 광채 드롭 섀도우 연동
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(229, 193, 153, 140)) # 웜 샌드 골드 빛번짐
        shadow.setOffset(0, 0)
        self.btn_emergency.setGraphicsEffect(shadow)
        
        right_layout.addWidget(self.btn_emergency)
        
        # [UI 개조] 🌐 비트겟 거래소 웹사이트 열기 버튼 (기존 RPA 복원 버튼 재활용)
        self.btn_reload_browser = QPushButton("🌐 비트겟 거래소 열기", right_widget)
        self.btn_reload_browser.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E6573, stop:1 #354752);
                color: #DEBA9D;
                font-weight: bold; 
                font-size: 11px; 
                padding: 6px; 
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5C7787, stop:1 #4E6573);
            }
        """)
        self.btn_reload_browser.clicked.connect(self.trigger_manual_reload_browser)
        right_layout.addWidget(self.btn_reload_browser)
        
        # BITGET 수동 제어판 (50% 청산, 스탑로스) -> 부모 위젯을 right_widget으로 계층 일원화하여 임시 유령 컨테이너 보더 생성 방어!
        self.lbl_bitget_title = QLabel("<b style='color:#FFFFFF; font-size: 11px;'>■ [BITGET] 수동 신속 제어판</b>", right_widget)
        right_layout.addWidget(self.lbl_bitget_title)
        
        # 1행: 🌓 50% 청산 버튼 (가로 100% 꽉 참)
        self.btn_close_50 = QPushButton("🌓 50% 청산", right_widget)
        self.btn_close_50.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E4944, stop:1 #35312E);
                color: #DEBA9D;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5C5550, stop:1 #4E4944);
            }
        """)
        self.btn_close_50.clicked.connect(self.trigger_close_50)
        right_layout.addWidget(self.btn_close_50)

        # 2행: 스탑 오프셋(%): 라벨 + [ 0.2 ]% 입력 박스 + 청산비율(%): 라벨 + [ 100 ]% 입력 박스
        offset_layout = QHBoxLayout()
        offset_layout.setContentsMargins(0, 0, 0, 0)
        offset_layout.setSpacing(4)

        lbl_offset = QLabel("오프셋(%):", right_widget)
        lbl_offset.setStyleSheet("color: #DEBA9D; font-size: 11px; font-weight: bold;")

        self.edit_stoploss_offset = QLineEdit("0.2", right_widget)
        self.edit_stoploss_offset.setMaximumWidth(45)
        self.edit_stoploss_offset.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, "AlignmentFlag") else Qt.AlignCenter)
        self.edit_stoploss_offset.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #00FFCC;
                font-family: Consolas;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #A88869;
                border-radius: 3px;
                padding: 3px;
            }
        """)

        lbl_ratio = QLabel("비율(%):", right_widget)
        lbl_ratio.setStyleSheet("color: #DEBA9D; font-size: 11px; font-weight: bold;")

        self.edit_stoploss_ratio = QLineEdit("100", right_widget)
        self.edit_stoploss_ratio.setPlaceholderText("100")
        self.edit_stoploss_ratio.setMaximumWidth(45)
        self.edit_stoploss_ratio.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, "AlignmentFlag") else Qt.AlignCenter)
        self.edit_stoploss_ratio.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #00FFCC;
                font-family: Consolas;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #A88869;
                border-radius: 3px;
                padding: 3px;
            }
        """)

        offset_layout.addWidget(lbl_offset)
        offset_layout.addWidget(self.edit_stoploss_offset)
        offset_layout.addWidget(lbl_ratio)
        offset_layout.addWidget(self.edit_stoploss_ratio)
        right_layout.addLayout(offset_layout)

        # 3행: 🛡️ 스마트 스탑 설정 버튼 (가로 100% 꽉 참)
        self.btn_stoploss = QPushButton("🛡️ 스마트 스탑 설정", right_widget)
        self.btn_stoploss.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E4944, stop:1 #35312E);
                color: #DEBA9D;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5C5550, stop:1 #4E4944);
            }
        """)
        self.btn_stoploss.clicked.connect(self.trigger_stoploss_setting)
        right_layout.addWidget(self.btn_stoploss)
        
        # ----------------------------------------------------------------------
        # ■ [BITGET] 실시간 목표가 가격 알림 제어판 (v3.65)
        # ----------------------------------------------------------------------
        lbl_alert_title = QLabel("■ [BITGET] 실시간 목표가 가격 알림", right_widget)
        lbl_alert_title.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold; margin-top: 10px;")
        right_layout.addWidget(lbl_alert_title)

        alert_input_layout = QHBoxLayout()
        alert_input_layout.setContentsMargins(0, 0, 0, 0)
        alert_input_layout.setSpacing(4)

        lbl_alert_target = QLabel("목표가($):", right_widget)
        lbl_alert_target.setStyleSheet("color: #DEBA9D; font-size: 11px; font-weight: bold;")

        self.edit_price_alert_target = QLineEdit("65000.0", right_widget)
        self.edit_price_alert_target.setPlaceholderText("65000.0")
        self.edit_price_alert_target.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, "AlignmentFlag") else Qt.AlignCenter)
        self.edit_price_alert_target.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #00FFCC;
                font-family: Consolas;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #A88869;
                border-radius: 3px;
                padding: 3px;
            }
        """)

        alert_input_layout.addWidget(lbl_alert_target)
        alert_input_layout.addWidget(self.edit_price_alert_target)
        right_layout.addLayout(alert_input_layout)

        alert_btn_layout = QHBoxLayout()
        alert_btn_layout.setContentsMargins(0, 0, 0, 0)
        alert_btn_layout.setSpacing(4)

        self.btn_price_alert_add = QPushButton("🔔 알림 등록", right_widget)
        self.btn_price_alert_add.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E4944, stop:1 #35312E);
                color: #DEBA9D;
                font-weight: bold;
                font-size: 11px;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5C5550, stop:1 #4E4944);
            }
        """)
        self.btn_price_alert_add.clicked.connect(self.add_price_alert)

        self.btn_price_alert_clear = QPushButton("❌ 전체 해제", right_widget)
        self.btn_price_alert_clear.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E4944, stop:1 #35312E);
                color: #DEBA9D;
                font-weight: bold;
                font-size: 11px;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #A88869;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5C5550, stop:1 #4E4944);
            }
        """)
        self.btn_price_alert_clear.clicked.connect(self.clear_price_alerts)

        alert_btn_layout.addWidget(self.btn_price_alert_add)
        alert_btn_layout.addWidget(self.btn_price_alert_clear)
        right_layout.addLayout(alert_btn_layout)

        self.lbl_active_price_alerts = QLabel("🔔 감시 중인 알림 없음", right_widget)
        self.lbl_active_price_alerts.setStyleSheet("color: #00FFCC; font-size: 11px; font-weight: bold; margin-top: 2px;")
        self.lbl_active_price_alerts.setWordWrap(True)
        right_layout.addWidget(self.lbl_active_price_alerts)
        
        
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

        right_layout.addStretch()
        
        # ----------------------------------------------------------------------
        # 국왕 폐하의 3박스 대통합 스케치 레이아웃 조립 집행
        # ----------------------------------------------------------------------
        # 하단 좌측: 컴팩트 로그 패널 (가로 70%) 복원 선언
        log_container_layout = QVBoxLayout()
        log_container_layout.setContentsMargins(18, 18, 18, 18) # 패널들간 완벽 대칭인 18px 패딩 주입
        log_container_layout.setSpacing(10)
        
        # 타이틀 라벨을 프레임 안쪽의 최상단 첫 줄로 안착시킴
        lbl_log_title = QLabel("<b style='color:#FFFFFF; font-size: 13px;'>■ [神선] 실시간 거래 로그 및 알림</b>")
        log_container_layout.addWidget(lbl_log_title)
        
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(200)  # [과부하 박멸] 초고속 200줄 자동 링버퍼 (HTML 파싱 0ms)
        self.txt_log.setStyleSheet("border: none; background-color: transparent; padding: 0px; font-family: 'Consolas', monospace; font-size: 11px; color: #D3C4BA;")
        log_container_layout.addWidget(self.txt_log)
        
        log_widget = QWidget()
        log_widget.setObjectName("log_panel")
        log_widget.setStyleSheet(panel_qss) # 놋쇠 황동 프레임 테두리 박스 씌움!
        log_widget.setLayout(log_container_layout)
        
        # 좌측 열 조립: 차트 패널 + 로그 패널 수직 정렬 (고정 높이 해제 및 stretch 7:3 배분)
        left_col_layout = QVBoxLayout()
        left_col_layout.setContentsMargins(0, 0, 0, 0)
        left_col_layout.setSpacing(18)
        
        left_col_layout.addWidget(center_widget, stretch=7)
        left_col_layout.addWidget(log_widget, stretch=3)
        
        # 좌측 2개 박스를 감싸는 전용 컨테이너 위젯 (고정 높이 족쇄 완전 해제하여 화면 크기에 반응형 연동)
        left_col_widget = QWidget()
        left_col_widget.setObjectName("left_col_widget")
        left_col_widget.setLayout(left_col_layout)
        
        # 우측 통박스: 자본설정/레이더/제어가 하나로 통합된 right_widget (높이 고정 족쇄 해제!)
        # QHBoxLayout의 자동 팽창 정렬 특성에 의해, 좌측 열 높이에 맞춰 자동으로 높이가 늘어남!
        # right_widget.setFixedHeight()를 완전히 생략하여 반응형 높이로 가동
        
        # 우측 제어판 스크롤 영역 적용 (소형 화면 및 노트북 해상도 대응)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
        scroll_area.setWidget(right_widget)
        
        # 전체 3분할 가로 레이아웃(panel_layout) 조립
        panel_layout.addWidget(left_col_widget, stretch=7)
        panel_layout.addWidget(scroll_area, stretch=3)
        
        main_layout.addLayout(panel_layout)
        
        self.add_log("Velvet Precision 웜 샌드 골드 럭셔리 대시보드 시동 완료.")
        if env_vars.get("BINANCE_API_KEY") or env_vars.get("BITGET_API_KEY"):
            self.add_log("보안 자격 증명 (client_config.json) 해석 및 API 키 연동 성공.")
        else:
            self.add_log("[안내] 모의 투자 시뮬레이션 모드로 가동이 준비되었습니다.")

    
    def request_csv_download(self):
        if hasattr(self, 'ws') and self.ws:
            import json
            asyncio.create_task(self.ws.send(json.dumps({'cmd': 'CMD_REQ_CSV'})))
            self.add_log("[CSV] 💾 서버에 데이터 다운로드를 요청했습니다.")

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
                    self.send_config_to_server()
                    
                    async for message in ws:
                        data = json.loads(message)
                        msg_type = data.get('type')
                        payload = data.get('data', {})
                        
                        if msg_type == 'update':
                            if 'price' in data:
                                self.current_price = float(data['price'])
                                self.lbl_price.setText(f"BTC/USDT 실시간 가격: {self.current_price:,.1f} USDT")
                            if 'log' in data:
                                self.add_log(data['log'])
                            if 'liq' in data or 'liq_10s' in data:
                                liq_val = float(data.get('liq_10s', data.get('liq', 0.0)))
                                target_liq_val = float(data.get('target_liq', getattr(self, 'target_liq', 2000000.0)))
                                self.bar_liq.setRange(0, int(target_liq_val))
                                self.bar_liq.setValue(int(liq_val))
                                self.bar_liq.setFormat(f"1분 누적 청산: ${int(liq_val):,} / ${target_liq_val:,.0f}")
                        elif msg_type == 'EVT_CSV_DATA':
                            csv_content = payload.get('csv_text', '')
                            csv_path = os.path.join(BASE_DIR, "docs", "downloaded_shinseon_data.csv")
                            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                            with open(csv_path, 'w', encoding='utf-8') as f:
                                f.write(csv_content)
                            self.add_log(f"💾 [CSV] 서버 데이터 다운로드 완료! 저장 위치: {csv_path}")
                        elif msg_type == 'EVT_SYNC_BALANCE':
                            usdt_total = payload.get('usdt_total', 0.0)
                            self.lbl_capital_display.setText(f"총 가용 자본금: ${usdt_total:,.2f}")
                            self.add_log(f"✅ [잔고 동기화] 실전 계좌 잔고가 업데이트되었습니다: ${usdt_total:,.2f}")
                        elif msg_type == 'EVT_SYNC_POSITION':
                            has_pos = payload.get('has_position', False)
                            if has_pos:
                                side = payload.get('side', 'LONG')
                                contracts = payload.get('contracts', 0.0)
                                entry_price = payload.get('entry_price', 0.0)
                                leverage = payload.get('leverage', 10)
                                self.lbl_position_status.setText(f"진입/청산 상태:\n[{side} 진입 중: {contracts} BTC @ ${entry_price:,.1f} ({leverage}x)]")
                                self.add_log(f"✅ [포지션 동기화] {side} 진입 중: {contracts} BTC @ ${entry_price:,.1f} ({leverage}x)")
                            else:
                                self.lbl_position_status.setText("진입/청산 상태:\n[100% 현금 대기 중]")
                                self.add_log("✅ [포지션 동기화] 활성 포지션 없음 (100% 현금 대기 중)")
                        elif msg_type == 'EVT_SYNC_ERROR':
                            err_msg = payload.get('error', '알 수 없는 오류')
                            self.add_log(f"❌ [잔고 동기화 실패] 서버 오류: {err_msg}")
                        elif msg_type == 'ui_update':
                            if 'price' in payload:
                                self.current_price = float(payload['price'])
                                self.lbl_price.setText(f"BTC/USDT 실시간 가격: {self.current_price:,.1f} USDT")
                            if 'msg' in payload and payload['msg']:
                                self.add_log(payload['msg'])
                            
                            # 오더플로우 레이더 UI 동적 연동 (V4.24): 하드코딩 $2.0M 제거 및 실시간 수신 세션/target_liq 포매팅
                            current_sess = payload.get('current_session', getattr(self, 'current_session', '로딩 중'))
                            t_liq = float(payload.get('target_liq', getattr(self, 'target_liq', 2000000.0)))
                            t_oi = float(payload.get('target_oi', getattr(self, 'target_oi', 1.0)))
                            l_10s = float(payload.get('liq_10s', 0.0))
                            o_spd = float(payload.get('oi_speed', 0.0))
                            p_ms = float(payload.get('ping_ms', 0.0))
                            p_stat = payload.get('poison_status', '정상 가동 중')
                            long_l = float(payload.get('long_liq', 0.0))
                            short_l = float(payload.get('short_liq', 0.0))
                            exp_dir = payload.get('expected_dir', 'LONG')

                            self.update_live_ui(
                                price=self.current_price,
                                guardrail_stage=1,
                                signal_text=payload.get('msg', ''),
                                liq_10s=l_10s,
                                oi_speed=o_spd,
                                ping_ms=p_ms,
                                poison_status=p_stat,
                                current_session=current_sess,
                                target_liq=t_liq,
                                target_oi=t_oi,
                                long_liq=long_l,
                                short_liq=short_l,
                                expected_dir=exp_dir
                            )
                        elif msg_type == 'csv_data':
                            csv_content = data.get('content')
                            with open('downloaded_data.csv', 'w', encoding='utf-8') as f:
                                f.write(csv_content)
                            self.add_log("[CSV] 데이터 다운로드 완료 및 저장 성공!")
            except Exception as e:
                self.add_log(f"[Websocket] 연결 오류: {e}. 3초 후 재시도...")
                await asyncio.sleep(3)

    def add_log(self, text):
        now = time.time()
        if hasattr(self, 'last_log_text') and self.last_log_text == text:
            if now - getattr(self, 'last_log_time', 0) < 1.0:
                return
        self.last_log_text = text
        self.last_log_time = now
        
        log_msg = f"[{time.strftime('%H:%M:%S')}] {text}"
        self.txt_log.appendPlainText(log_msg)
        
        # 비동기 로그 작성 큐에 넣기 (모든 실시간 거래/상태 로그 100% 영구 보존 - 기획서_23)
        try:
            file_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n"
            self.log_queue.put_nowait(file_msg)
        except Exception:
            pass

    async def log_writer_daemon(self):
        while True:
            try:
                msg = await self.log_queue.get()
                batch = [msg]
                while not self.log_queue.empty():
                    try:
                        batch.append(self.log_queue.get_nowait())
                    except Exception:
                        break
                        
                current_date = datetime.now().strftime("%Y-%m-%d")
                log_file_path = os.path.join(BASE_DIR, "docs", "historical_data", f"shinseon_trade_{current_date}.log")
                
                def _write_batch(path, items):
                    try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "a", encoding="utf-8") as f:
                            f.writelines(items)
                    except Exception:
                        pass
                
                await asyncio.to_thread(_write_batch, log_file_path, batch)
                for _ in range(len(batch)):
                    self.log_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.2)


    def send_config_to_server(self):
        if hasattr(self, 'ws') and self.ws:
            try:
                config_payload = {
                    "session_thresholds": getattr(self, "session_thresholds", {}),
                    "session_guardrails": getattr(self, "session_guardrails", {}),
                    "leverage_level": getattr(self, "leverage_level", 30),
                    "betting_ratio": getattr(self, "betting_ratio", 400.0),
                    "split_entry_1_ratio": getattr(self, "split_entry_1_ratio", 250.0),
                    "split_entry_2_ratio": getattr(self, "split_entry_2_ratio", 100.0),
                    "split_entry_2_trigger_pct": getattr(self, "split_entry_2_trigger_pct", -0.3),
                    "split_entry_3_ratio": getattr(self, "split_entry_3_ratio", 50.0),
                    "split_entry_3_trigger_pct": getattr(self, "split_entry_3_trigger_pct", -0.6),
                    "split_cooldown_seconds": getattr(self, "split_cooldown_seconds", 900.0),
                    "cooldown_seconds": getattr(self, "cooldown_seconds", 60.0),
                    "profit_cooldown_seconds": getattr(self, "profit_cooldown_seconds", 15.0),
                    "half_exit_close_ratio": getattr(self, "half_exit_close_ratio", 50.0),
                    "pyramiding_enabled": getattr(self, "pyramiding_enabled", True),
                    "pyramiding_ratio": getattr(self, "pyramiding_ratio", 30.0),
                    "manual_threshold": self.chk_manual_threshold.isChecked(),
                    "target_liq": self.edit_target_liq.text(),
                    "target_oi": self.edit_target_oi.text(),
                    "target_slippage": self.edit_target_slippage.text()
                }
                packet = {"cmd": "CMD_UPDATE_CONFIG", "config": config_payload}
                asyncio.create_task(self.ws.send(json.dumps(packet)))
            except Exception as e:
                logger.error(f"서버 설정 전송 오류: {e}")

    def save_shinseon_config(self):
        try:
            config_path = os.path.join(BASE_DIR, "shinseon_config.json")
            config_data = {
                "CURRENT_VERSION": self.CURRENT_VERSION,
                "auto_start": getattr(self.bot_core.v35_engine, "is_snipe_active", False) if self.bot_core.v35_engine else False,
                "manual_threshold": self.chk_manual_threshold.isChecked(),
                "target_liq": self.edit_target_liq.text(),
                "target_oi": self.edit_target_oi.text(),
                "target_slippage": self.edit_target_slippage.text(),
                "session_thresholds": self.session_thresholds,
                "leverage_level": self.leverage_level,
                "betting_ratio": self.betting_ratio,
                "split_entry_1_ratio": self.split_entry_1_ratio,
                "split_entry_2_ratio": self.split_entry_2_ratio,
                "split_entry_2_trigger_pct": self.split_entry_2_trigger_pct,
                "split_entry_3_ratio": self.split_entry_3_ratio,
                "split_entry_3_trigger_pct": self.split_entry_3_trigger_pct,
                "split_cooldown_seconds": self.split_cooldown_seconds,
                "cooldown_seconds": self.cooldown_seconds,
                "profit_cooldown_seconds": self.profit_cooldown_seconds,
                "telegram_enabled": self.telegram_enabled,
                "telegram_token": self.telegram_token,
                "telegram_chat_id": self.telegram_chat_id,
                "sound_enabled": getattr(self, "sound_enabled", True),
                "half_exit_enabled": self.half_exit_enabled,
                "half_exit_trigger_pct": self.half_exit_trigger_pct,
                "half_exit_close_ratio": self.half_exit_close_ratio,
                "entry_sl_guard_pct": self.entry_sl_guard_pct,
                "session_guardrails": self.session_guardrails,
                "pyramiding_enabled": self.pyramiding_enabled,
                "pyramiding_ratio": self.pyramiding_ratio
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            self.send_config_to_server()
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")

    def load_shinseon_config(self):
        try:
            config_path = os.path.join(BASE_DIR, "shinseon_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                
                self.CURRENT_VERSION = config_data.get("CURRENT_VERSION", self.CURRENT_VERSION)
                
                # 수동 임계치 체크박스 복구 (로딩 도중 상태 변경 신호가 발생하여 미완성 상태가 저장되는 루프 방지)
                self.chk_manual_threshold.blockSignals(True)
                is_manual = config_data.get("manual_threshold", False)
                self.chk_manual_threshold.setChecked(is_manual)
                self.chk_manual_threshold.blockSignals(False)
                
                # 입력 필드 복구
                self.edit_target_liq.setText(config_data.get("target_liq", "2,500,000"))
                self.edit_target_oi.setText(config_data.get("target_oi", "0.12"))
                self.edit_target_slippage.setText(config_data.get("target_slippage", "0.15"))
                
                # 신규 설정 변수 복구
                self.session_thresholds = config_data.get("session_thresholds", self.session_thresholds)
                self.leverage_level = config_data.get("leverage_level", self.leverage_level)
                self.betting_ratio = config_data.get("betting_ratio", self.betting_ratio)
                self.split_entry_1_ratio = config_data.get("split_entry_1_ratio", 250.0)
                self.split_entry_2_ratio = config_data.get("split_entry_2_ratio", 100.0)
                self.split_entry_2_trigger_pct = config_data.get("split_entry_2_trigger_pct", -0.3)
                self.split_entry_3_ratio = config_data.get("split_entry_3_ratio", 50.0)
                self.split_entry_3_trigger_pct = config_data.get("split_entry_3_trigger_pct", -0.6)
                self.split_cooldown_seconds = config_data.get("split_cooldown_seconds", 900.0)
                self.cooldown_seconds = config_data.get("cooldown_seconds", 60.0)
                self.profit_cooldown_seconds = config_data.get("profit_cooldown_seconds", 15.0)
                
                # 텔레그램 설정 복구 (개발계획서_178)
                self.telegram_enabled = config_data.get("telegram_enabled", False)
                self.telegram_token = config_data.get("telegram_token", "")
                self.telegram_chat_id = config_data.get("telegram_chat_id", "")
                self.sound_enabled = config_data.get("sound_enabled", True)
                self.half_exit_enabled = config_data.get("half_exit_enabled", True)
                self.half_exit_trigger_pct = config_data.get("half_exit_trigger_pct", 0.6)
                self.half_exit_close_ratio = config_data.get("half_exit_close_ratio", 50.0)
                self.entry_sl_guard_pct = config_data.get("entry_sl_guard_pct", 0.0)
                
                loaded_guardrails = config_data.get("session_guardrails", {})
                default_guardrails = {
                    "ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
                    "LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
                    "NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
                    "PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True},
                    "WEEKEND_ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
                    "WEEKEND_LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
                    "WEEKEND_NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
                    "WEEKEND_PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True}
                }
                for k, v in default_guardrails.items():
                    if k not in loaded_guardrails:
                        loaded_guardrails[k] = v
                self.session_guardrails = loaded_guardrails

                default_thresholds = {
                    "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
                    "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
                    "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
                    "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True},
                    "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
                    "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
                    "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
                    "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True}
                }
                for k, v in default_thresholds.items():
                    if k not in self.session_thresholds:
                        self.session_thresholds[k] = v
                    elif "enabled" not in self.session_thresholds[k]:
                        self.session_thresholds[k]["enabled"] = True
                self.pyramiding_enabled = config_data.get("pyramiding_enabled", True)
                self.pyramiding_ratio = config_data.get("pyramiding_ratio", 30.0)
                
                # 비활성화 상태 스타일 보정 트리거
                self.toggle_manual_threshold_inputs()
                
                # [29차 과업] 앱 기동 시 무조건 정지 모드로 구동 (auto_start = False 고정)
                self.auto_start = False
                if self.bot_core and getattr(self.bot_core, "v35_engine", None):
                    self.bot_core.v35_engine.is_snipe_active = False
                
                # [버전 동기화 보정] 로딩 완료 후 윈도우 타이틀 및 메인 브랜드 라벨 버전 동기화
                self.setWindowTitle(f"[神選 : 신선 (신의 선택)] 마스터 대시보드 {self.CURRENT_VERSION}")
                if hasattr(self, "lbl_brand") and self.lbl_brand:
                    self.lbl_brand.setText(
                        "<span style='color: #DEBA9D; font-weight: bold; font-size: 20px; font-family: \"Georgia\", serif;'>神選 [SHINSEON]</span> "
                        "<span style='font-size: 16px; font-weight: bold; color: #F5EFEB; font-family: \"Segoe UI\";'>- 신의 선택 마스터 터미널</span> "
                        f"<span style='font-size: 11px; font-weight: bold; color: #C5A07A; border: 1px solid rgba(222, 186, 157, 0.35); border-radius: 3px; padding: 2px 6px; margin-left: 8px; vertical-align: middle;'>{self.CURRENT_VERSION}</span>"
                    )
        except Exception as e:
            logger.error(f"설정 파일 로딩 실패: {e}")

    def start_bot_auto_recovery(self):
        if self.bot_core.v35_engine and not self.bot_core.v35_engine.is_snipe_active:
            self.start_bot()
            self.add_log("🔄 [자동 복구] 이전 세션 상태를 복구하여 자동 저격 가동을 개시했습니다.")

    def stop_bot(self):
        if not self.bot_core.v35_engine:
            return
        if self.bot_core.v35_engine.is_snipe_active:
            self.start_bot()

    def send_telegram_notification(self, text):
        if not self.telegram_enabled or not self.telegram_token or not self.telegram_chat_id:
            return
        
        async def _async_send():
            def run():
                import urllib.parse
                import urllib.request
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                data = urllib.parse.urlencode({
                    "chat_id": self.telegram_chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }).encode("utf-8")
                req = urllib.request.Request(url, data=data, method="POST")
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.read()
            try:
                await asyncio.to_thread(run)
            except Exception as e:
                self.add_log(f"❌ [텔레그램] 알림 발송 실패: {e}")
                
        asyncio.create_task(_async_send())

    def handle_telegram_command(self, text):
        cmd = text.strip()
        if cmd in ["/시작", "시작"]:
            if self.bot_core.v35_engine and not self.bot_core.v35_engine.is_snipe_active:
                self.start_bot()
                self.send_telegram_notification("<b>▶ [원격 제어]</b> 자동 봇 감시가 가동되었습니다. (실물 진입 허용)")
            else:
                self.send_telegram_notification("<b>▶ [원격 제어]</b> 자동 봇 감시가 이미 작동 중입니다.")
        elif cmd in ["/정지", "정지"]:
            if self.bot_core.v35_engine and self.bot_core.v35_engine.is_snipe_active:
                self.stop_bot()
                self.send_telegram_notification("<b>⏸ [원격 제어]</b> 자동 봇 감시를 대기 모드로 해제했습니다.")
            else:
                self.send_telegram_notification("<b>⏸ [원격 제어]</b> 자동 봇 감시가 이미 대기 상태입니다.")
        elif cmd in ["/청산", "청산", "/전량청산", "전량청산"]:
            if self.bot_core.v35_engine and self.bot_core.v35_engine.is_position_active:
                self.bot_core.v35_engine.exit_reason = "텔레그램 원격 비상 전량 청산"
                asyncio.create_task(self.bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED"))
                self.send_telegram_notification("<b>🚨 [원격 비상 청산]</b> 텔레그램 명령으로 현재 열린 포지션을 100% 즉시 시장가 강제 청산 집행합니다!")
            else:
                self.send_telegram_notification("<b>⚠️ [원격 제어]</b> 청산할 오픈 포지션이 없습니다. (100% 현금 대기 중)")
        elif cmd in ["/상태", "상태"]:
            asyncio.create_task(self.do_telegram_status_command())
            
    async def do_telegram_status_command(self):
        try:
            is_active = self.bot_core.v35_engine.is_snipe_active if self.bot_core.v35_engine else False
            active_str = "🟢 감시 가동 중" if is_active else "🔴 대기 상태"
            
            btc_price = getattr(self.bot_core, "current_price", 0.0)
            if btc_price <= 0.0 and hasattr(self, "last_price"):
                btc_price = self.last_price
            
            session_info = getattr(self, "last_current_session", "알 수 없음")
            liq_10s = getattr(self, "last_liq_10s", 0.0)
            oi_speed = getattr(self, "last_oi_speed", 0.0)
            
            val_bal = getattr(self, "last_balance", 0.0)
            if val_bal > 0.0:
                balance_str = f"${val_bal:,.2f}"
            else:
                balance_str = "조회 대기 중"
            
            pos_active = self.bot_core.v35_engine.is_position_active if (self.bot_core.v35_engine) else False
            
            pos_str = ""
            if pos_active:
                direction = getattr(self.bot_core.v35_engine, "entry_direction", "LONG")
                entry_price = getattr(self.bot_core.v35_engine, "entry_price", 0.0)
                pnl_pct = 0.0
                if entry_price > 0.0:
                    if direction == "LONG":
                        pnl_pct = (btc_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - btc_price) / entry_price
                
                volume = getattr(self.bot_core.v35_engine, "position_volume", 0)
                qty_btc = volume / 1000.0
                
                pnl_usdt = 0.0
                if qty_btc > 0.0 and entry_price > 0.0 and btc_price > 0.0:
                    if direction == "LONG":
                        pnl_usdt = qty_btc * (btc_price - entry_price)
                    else:
                        pnl_usdt = qty_btc * (entry_price - btc_price)
                else:
                    pnl_usdt = getattr(self, "last_pnl_usdt", 0.0)
                
                pos_str = (
                    f"🔹 포지션: <b>{direction}</b>\n"
                    f"🔹 포지션 수량: <b>{qty_btc:.3f} BTC</b>\n"
                    f"🔹 진입 평단: <b>{entry_price:,.1f} USDT</b>\n"
                    f"🔹 현재 가격: <b>{btc_price:,.1f} USDT</b>\n"
                    f"🔹 미실현 수익률: <b>{pnl_pct*100:+.2f}%</b>\n"
                    f"🔹 현재 PNL: <b>{pnl_usdt:+.2f} USDT</b>"
                )
            else:
                pos_str = "🔹 포지션: <b>진입 대기 중 (포지션 없음)</b>"
                
            msg = (
                f"<b>📊 [신선 봇 현재 상태 보고]</b>\n\n"
                f"▪️ 자동감시 가동: {active_str}\n"
                f"▪️ 가용 자본금: <b>{balance_str}</b>\n"
                f"▪️ 세션 정보: <b>{session_info}</b>\n"
                f"▪️ 실시간 가격: <b>{btc_price:,.1f} USDT</b>\n"
                f"▪️ 1분 누적 청산: <b>${liq_10s:,.0f}</b>\n"
                f"▪️ 1분 OI 속도: <b>{oi_speed:+.4f}%</b>\n\n"
                f"{pos_str}"
            )
            self.send_telegram_notification(msg)
        except Exception as e:
            self.add_log(f"❌ [텔레그램] 상태 명령 처리 중 에러 발생: {e}")

    async def run_telegram_listener_loop(self):
        last_update_id = 0
        is_first = True
        while True:
            await asyncio.sleep(2.0)
            if not self.telegram_enabled or not self.telegram_token or not self.telegram_chat_id:
                is_first = True
                continue
                
            def get_updates():
                try:
                    import urllib.request
                    import json
                    url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates?timeout=5"
                    if last_update_id > 0:
                        url += f"&offset={last_update_id}"
                    
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=10) as r:
                        return json.loads(r.read().decode("utf-8"))
                except Exception as e:
                    return e
            
            res = await asyncio.to_thread(get_updates)
            if isinstance(res, Exception):
                self.add_log(f"⚠️ [텔레그램] 수신 에러: {res}")
                continue
                
            if res and res.get("ok"):
                updates = res.get("result", [])
                if updates:
                    for update in updates:
                        update_id = update.get("update_id")
                        if update_id >= last_update_id:
                            last_update_id = update_id + 1
                            
                        if is_first:
                            continue
                            
                        message = update.get("message", {})
                        chat = message.get("chat", {})
                        chat_id = str(chat.get("id", ""))
                        
                        if chat_id != str(self.telegram_chat_id).strip():
                            continue
                            
                        text = message.get("text", "")
                        if text:
                            self.add_log(f"📲 [텔레그램] 명령 수신: {text}")
                            self.handle_telegram_command(text)
                    is_first = False
                else:
                    is_first = False

    def show_session_config_dialog(self):
        try:
            self.add_log("⚙️ [설정] 세션 및 트레이딩 핵심 설정 대화상자를 호출합니다.")
            dialog = ShinseonConfigDialog(self)
            dialog.exec()
        except Exception as ex:
            logger.error(f"설정 창 구동 실패: {ex}")
            self.add_log(f"⚠️ [설정 에러] 설정 창 팝업 실패: {ex}")

    def closeEvent(self, event):
        self.save_shinseon_config()
        event.accept()

    def generate_initial_candles(self):
        # 트레이딩뷰 위젯이 자체 렌더링하므로 연산 제거
        pass

    def update_chart(self):
        # 트레이딩뷰 위젯이 담당하므로 연산 제거
        pass

    def calculate_proportions(self):
        try:
            # 총자본 라벨 텍스트 파싱하여 수동 적용에 폴백 작동
            capital_text = self.lbl_capital_display.text().replace("총 가용 자본금:", "").replace("$", "").replace(",", "").strip()
            if "대기" in capital_text or not capital_text:
                c_total = 20000.0
            else:
                c_total = float(capital_text)
            
            m_bitget = c_total
            m_bin = 0.0
            bitget_bal = getattr(self.bot_core, "bitget_balance", 0.0)
            if bitget_bal <= 0.0:
                bitget_bal = c_total
            p_target = max(1000.0, bitget_bal * (self.betting_ratio / 100.0))
            
            self.bot_core.update_capital_config(c_total, m_bitget, m_bin, p_target)
            self.add_log(f"자본 비율 실시간 리밸런싱 완료 ➡️ 총자본: ${c_total:,.2f}, 목표 포지션 규모: ${p_target:,.2f}")
        except ValueError:
            c_total_fallback = 20000.0
            m_bitget = c_total_fallback
            m_bin = 0.0
            bitget_bal = getattr(self.bot_core, "bitget_balance", 0.0)
            if bitget_bal <= 0.0:
                bitget_bal = c_total_fallback
            p_target = max(1000.0, bitget_bal * (self.betting_ratio / 100.0))
            
            self.bot_core.update_capital_config(c_total_fallback, m_bitget, m_bin, p_target)

    def sync_account_balances(self):
        self.btn_sync_balance.setEnabled(False)
        self.btn_sync_balance.setText("🔄 잔고 조회 중...")
        self.add_log("[자산 조회] 실계좌 실시간 자본 동기화 개시...")
        asyncio.create_task(self.do_sync_balances())

    async def do_sync_balances(self):
        self.add_log("[뷰어 모드] 잔고 동기화 명령을 서버로 전송합니다.")
        if hasattr(self, 'ws') and self.ws:
            try:
                await self.ws.send(json.dumps({"cmd": "CMD_SYNC_POSITION"}))
            except Exception as e:
                self.add_log(f"❌ [웹소켓 에러] 잔고 동기화 전송 실패: {e}")
        else:
            self.add_log("❌ [웹소켓 에러] 서버 연결이 끊어졌거나 연결 중입니다.")
        self.btn_sync_balance.setEnabled(True)
        self.btn_sync_balance.setText("🔄 실전 계좌 잔고 동기화")
    def toggle_manual_threshold_inputs(self):
        # 수동 임계치 체크되어 있을때(True) 수정 못함(False), 체크 풀면(False) 수정 가능(True)
        is_checked = self.chk_manual_threshold.isChecked()
        self.edit_target_liq.setEnabled(not is_checked)
        self.edit_target_oi.setEnabled(not is_checked)
        self.edit_target_slippage.setEnabled(not is_checked)

    def trigger_position_sync(self):
        self.btn_position_sync.setEnabled(False)
        self.btn_position_sync.setText("🔄 동기화 중...")
        self.add_log("[수동 리로드] BITGET 포지션 강제 재동기화 개시...")
        asyncio.create_task(self.do_position_sync())

    async def do_position_sync(self):
        try:
            if hasattr(self, 'ws') and self.ws:
                import json
                await self.ws.send(json.dumps({"cmd": "CMD_SYNC_POSITION"}))
                self.add_log("📡 [서버 명령] 포지션 동기화 명령을 서버로 전송했습니다.")
            else:
                self.add_log("❌ [오류] 서버 웹소켓 연결이 없습니다.")
        except Exception as e:
            self.add_log(f"❌ [동기화 실패] 명령 전송 중 오류 발생: {e}")
        finally:
            self.btn_position_sync.setEnabled(True)
            self.btn_position_sync.setText("🔄 포지션 동기화")
            
    async def run_startup_sync_sequence(self):
        """부팅 시 3대 핵심 요소 자동 동기화 시퀀스집행"""
        # [신규] 루트 로그 자동 마이그레이션 구문 (개발계획서_183, 184 고도화)
        try:
            legacy_log_path = os.path.join(BASE_DIR, "shinseon_trade.log")
            if os.path.exists(legacy_log_path):
                current_date = datetime.now().strftime("%Y-%m-%d")
                target_log_path = os.path.join(BASE_DIR, "docs", "historical_data", f"shinseon_trade_{current_date}.log")
                os.makedirs(os.path.dirname(target_log_path), exist_ok=True)
                
                # 기존 로그 내용을 라인별로 읽기
                with open(legacy_log_path, "r", encoding="utf-8") as f_in:
                    legacy_lines = f_in.readlines()
                
                # 오직 🎯 가 포함된 줄만 필터링하여 당일 자 로그 파일 끝에 추가
                filtered_lines = [line for line in legacy_lines if "🎯" in line]
                if filtered_lines:
                    with open(target_log_path, "a", encoding="utf-8") as f_out:
                        f_out.writelines(filtered_lines)
                
                # 기존 루트 로그 파일 물리적 삭제
                os.remove(legacy_log_path)
                self.add_log("⚙️ [마이그레이션] 이전 거래 로그(shinseon_trade.log)에서 🎯 핵심 로그만 당일 일별 로그 파일로 병합 및 원본 삭제 완수.")
        except Exception as e:
            self.add_log(f"⚠️ [마이그레이션 실패] 이전 거래 로그 마이그레이션 중 오류 발생: {e}")

        # 로그 라이터 데몬 비동기 루프 기동 (개발계획서_175)
        asyncio.create_task(self.log_writer_daemon())
        # 텔레그램 원격 명령어 수신 비동기 루프 기동 (개발계획서_178)
        asyncio.create_task(self.run_telegram_listener_loop())
        self.add_log("🚀 [부팅 시퀀스] 자동 동기화 및 라이선스 검증 시퀀스를 개시합니다...")
        
        # 1. 라이선스 비동기 검증 집행 (메인 UI 프리징 해결)
        self.add_log("🔒 [라이선스 검증] GitHub 라이선스 온라인 인증을 수행하는 중...")
        try:
            hw_id = await asyncio.to_thread(get_hardware_uuid)
            is_licensed, reason = await asyncio.to_thread(check_license_online, hw_id)
            if not is_licensed:
                self.add_log(f"❌ [인증 실패] 라이선스 인증 실패: {reason}")
                
                # 메인 스레드에서 다이얼로그 호출 및 즉시 종료
                dialog = ShinseonLicenseDialog(hw_id, reason, parent=self)
                dialog.exec()
                sys.exit(0)
            self.add_log(f"✔ [인증 완료] 정식 라이선스가 확인되었습니다. {reason}")
        except Exception as license_err:
            self.add_log(f"❌ [인증 에러] 라이선스 검증 오류 발생: {license_err}")
            sys.exit(0)
            
        # 2. 통합 동기화 단계 (잔고 + 포지션)
        self.add_log("⚡ [부팅 동기화 1/2] 실전 계좌 잔고 및 포지션 상태 통합 동기화 시동...")
        await self.do_sync_balances()
        
        # 3. 레이턴시 물리 실측 백그라운드 구동
        self.add_log("⚡ [부팅 동기화 2/2] 5초간 바이낸스-BITGET 레이턴시 물리 실측 백그라운드 개시...")
        self.trigger_latency_test()
        
        # 4. 비트겟 사이트 자동 팝업 (사용자 요청)
        import webbrowser
        try:
            webbrowser.open_new("https://www.bitget.com/futures/usdt/BTCUSDT")
            self.add_log("🌐 [비트겟 거래소] 초기 구동 시 비트겟 거래소 화면을 띄웠습니다.")
        except Exception as e:
            pass



    def start_bot(self):
        try:
            if hasattr(self, 'ws') and self.ws:
                import json
                if self.btn_start.text() == "▶ 자동 봇 시작":
                    asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_START_BOT"})))
                    self.add_log("📡 [서버 명령] 자동 저격 감시 시작 명령을 서버로 전송했습니다.")
                    self.btn_start.setText("⏸ 자동 봇 정지")
                    self.btn_start.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2E6B4E, stop:1 #1B4530);
                            color: #F5EFEB;
                            font-weight: bold; 
                            font-size: 13px; 
                            padding: 11px; 
                            border-radius: 4px;
                            border: 1px solid #1E5037;
                            border-top: 1.5px solid rgba(255, 255, 255, 0.35);
                        }
                    """)
                    self.btn_manual_start.setEnabled(False)
                else:
                    asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_STOP_BOT"})))
                    self.add_log("📡 [서버 명령] 자동 저격 감시 중지 명령을 서버로 전송했습니다.")
                    self.btn_start.setText("▶ 자동 봇 시작")
                    self.btn_start.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DEBA9D, stop:1 #C5A07A);
                            color: #0F0E0E;
                            font-weight: bold; 
                            font-size: 13px; 
                            padding: 11px; 
                            border-radius: 4px;
                            border: 1px solid #A88869;
                            border-top: 1.5px solid rgba(255, 255, 255, 0.35);
                        }
                        QPushButton:hover {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #DEBA9D);
                        }
                    """)
                    self.btn_manual_start.setEnabled(True)
            else:
                self.add_log("❌ [오류] 서버 웹소켓 연결이 없습니다.")
        except Exception as e:
            self.add_log(f"❌ [봇 제어 실패] {e}")
        self.save_shinseon_config()
        
    def manual_start_bot(self):
        if not self.bot_core.v35_engine:
            self.add_log("[오류] 백엔드 엔진이 준비되지 않았습니다.")
            return
            
        # 만약 이미 수동 가드가 켜져 있는 상태라면 -> 정지(토글) 처리!
        if self.bot_core.v35_engine.is_position_active:
            self.bot_core.v35_engine.is_position_active = False
            self.btn_manual_start.setText("⚡ 수동 봇 시작")
            self.btn_manual_start.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8C7355, stop:1 #594733);
                    color: #F5EFEB;
                    font-weight: bold; 
                    font-size: 13px; 
                    padding: 11px; 
                    border-radius: 4px;
                    border: 1px solid #735D43;
                    border-top: 1.5px solid rgba(255, 255, 255, 0.25);
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A18663, stop:1 #8C7355);
                }
            """)
            # 자동 버튼 상호 잠금 해제
            self.btn_start.setEnabled(True)
            self.add_log("⏸ [하이브리드 수동 감시] 수동 진입 포지션 가드레일 감시를 전격 중단합니다.")
            
            # 거래소 예약 주문 일괄 취소 코루틴 발진 (스탑로스 완전 정화)
            asyncio.create_task(self.cancel_all_bitget_trigger_orders_internal())
            return
            
        # 버튼을 잠시 비활성화하고 '동기화 및 가동 중...' 상태로 전환
        self.btn_manual_start.setEnabled(False)
        self.btn_manual_start.setText("⚡ 동기화 및 가동 중...")
        self.btn_manual_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #C5A07A);
                color: #0F0E0E;
                font-weight: bold; 
                font-size: 13px; 
                padding: 11px; 
                border-radius: 4px;
                border: 1px solid #735D43;
                border-top: 1.5px solid rgba(255, 255, 255, 0.25);
            }
        """)

        async def run_manual_start_flow():
            try:
                self.add_log("[수동 가동 시작] BITGET 실시간 포지션 사전 동기화 수행 중...")
                await self.do_position_sync()

                direction = getattr(self.bot_core.v35_engine, "entry_direction", None)
                is_active = getattr(self.bot_core.v35_engine, "is_position_active", False)

                if not direction or not is_active:
                    self.add_log("❌ [가동 실패] BITGET 포지션이 비어 있거나 로드되지 않았습니다. 거래소 탭에 포지션이 열려 있는지 확인해 주십시오.")
                    # 버튼 원래 상태로 복구
                    self.btn_manual_start.setEnabled(True)
                    self.btn_manual_start.setText("⚡ 수동 봇 시작")
                    self.btn_manual_start.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8C7355, stop:1 #594733);
                            color: #F5EFEB;
                            font-weight: bold; 
                            font-size: 13px; 
                            padding: 11px; 
                            border-radius: 4px;
                            border: 1px solid #735D43;
                            border-top: 1.5px solid rgba(255, 255, 255, 0.25);
                        }
                        QPushButton:hover {
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A18663, stop:1 #8C7355);
                        }
                    """)
                    return

                # 포지션이 정상 감지되었으면 가이드라인 가동 및 평단가 설정
                actual_entry_price = self.bot_core.v35_engine.entry_price
                if actual_entry_price <= 0.0:
                    actual_entry_price = await self.bot_core.v35_engine.get_live_bitget_price_internal()
                if actual_entry_price <= 0.0:
                    actual_entry_price = float(self.bot_core.current_price)

                self.bot_core.v35_engine.entry_price = actual_entry_price
                self.bot_core.v35_engine.peak_pnl_pct = 0.0
                self.bot_core.v35_engine.is_position_active = True

                import time
                self.bot_core.v35_engine.grace_period_until = time.time() + 3.0

                # UI 업데이트 및 활성화
                self.btn_manual_start.setEnabled(True)
                self.btn_manual_start.setText("⏸ 수동 봇 정지")
                self.btn_manual_start.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5C5550, stop:1 #4E4944);
                        color: #DEBA9D;
                        font-weight: bold; 
                        font-size: 13px; 
                        padding: 11px; 
                        border-radius: 4px;
                        border: 1px solid #423E3B;
                        border-top: 1.5px solid rgba(255, 255, 255, 0.2);
                    }
                """)
                self.btn_start.setEnabled(False)

                self.add_log(f"⚡ [하이브리드 수동 감시] BITGET 진입 평단가 ${actual_entry_price:,.1f} 기준으로 진입 평단가를 캘리브레이션 완료하였습니다. (3초 오작동 유예 가동)")
                self.add_log(f"⚡ [하이브리드 오토-청산] 수동 진입 포지션 가드레일 감시 자동 도킹 개시 (방향: {direction})")

                asyncio.create_task(self.bot_core.v35_engine.execute_bitget_internal_packet(
                    side="STOP_LOSS", 
                    order_type=str(round(actual_entry_price * 1.013 if direction == "SHORT" else actual_entry_price * 0.987, 1))
                ))

                asyncio.create_task(self.bot_core.v35_engine.manage_v35_exit_guardrail(direction))

            except Exception as e:
                self.add_log(f"❌ [가동 실패] 수동 가동 중 예외 발생: {e}")
                self.btn_manual_start.setEnabled(True)
                self.btn_manual_start.setText("⚡ 수동 봇 시작")
                self.btn_manual_start.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8C7355, stop:1 #594733);
                        color: #F5EFEB;
                        font-weight: bold; 
                        font-size: 13px; 
                        padding: 11px; 
                        border-radius: 4px;
                        border: 1px solid #735D43;
                        border-top: 1.5px solid rgba(255, 255, 255, 0.25);
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A18663, stop:1 #8C7355);
                    }
                """)

        asyncio.create_task(run_manual_start_flow())

    async def execute_bitget_emergency_master_internal(self):
        pass

    async def cancel_all_bitget_trigger_orders_internal(self):
        self.add_log("[스탑로스 정화] BITGET 거래소의 모든 미체결 스탑 예약 주문 취소 진행 중...")
        try:
            # v1.1 성능 격상: DOM 매크로를 걷어내고 API 패킷 직송 함수로 이관
            await self.bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="CANCEL_ALL")
            self.add_log("[스탑로스 정화 완료] API 패킷 직송을 통한 정화 시퀀스 완료")
        except Exception as e:
            self.add_log(f"❌ [스탑로스 정화 실패] 오류 발생: {e}")
        
    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self.load_lazy_chart)

    def load_lazy_chart(self):
        if getattr(self, "chart_loaded", False):
            return
        self.chart_loaded = True
        
        chart_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                html, body { margin: 0; padding: 0; width: 100%; height: 100%; background-color: #141312; overflow: hidden; }
                #tradingview_widget { width: 100%; height: 100%; }
            </style>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        </head>
        <body>
            <div id="tradingview_widget"></div>
            <script type="text/javascript">
            new TradingView.widget({
              "autosize": true,
              "symbol": "BINANCE:BTCUSDT.P",
              "interval": "15",
              "timezone": "Asia/Seoul",
              "theme": "dark",
              "style": "1",
              "locale": "kr",
              "toolbar_bg": "#141312",
              "enable_publishing": false,
              "hide_legend": false,
              "save_image": false,
              "container_id": "tradingview_widget",
              "studies": [
                "STD;MACD"
              ]
            });
            </script>
        </body>
        </html>
        """
        self.chart_view.setHtml(chart_html, QUrl("https://s3.tradingview.com"))
        self.add_log("트레이딩뷰 실시간 순정 고급 차트 엔진(tv.js) 원복 로딩 완료.")
        
        # [상시 통신 작동] 앱 구동과 동시에 백엔드 시세/레이더 감시 상시 백그라운드 기동!
        self.add_log("★ [雷達] 실시간 오더플로우 레이더 웹소켓 감시 엔진 상시 구동 개시.")
        asyncio.create_task(self.bot_core.run_engine(self.update_live_ui, self.set_live_candles))

    def emergency_close(self):
        self.add_log("🚨 [긴급 탈출] 긴급 정지 및 청산 명령을 서버로 전송합니다!")
        
        if hasattr(self, 'ws') and self.ws:
            import json
            asyncio.create_task(self.ws.send(json.dumps({"cmd": "CMD_STOP_BOT"})))
            self.add_log("📡 [서버 명령] 긴급 중지 명령 전송 완료")
        else:
            self.add_log("❌ [오류] 서버 웹소켓 연결이 없습니다.")
        
        # 4. 버튼 2개 비주얼 및 상호 잠금 상태 완전 해금 원복
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶ 자동 봇 시작")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #DEBA9D, stop:1 #C5A07A);
                color: #0F0E0E;
                font-weight: bold; 
                font-size: 13px; 
                padding: 11px; 
                border-radius: 4px;
                border: 1px solid #A88869;
                border-top: 1.5px solid rgba(255, 255, 255, 0.35);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E5C199, stop:1 #DEBA9D);
            }
        """)
        
        self.btn_manual_start.setEnabled(True)
        self.btn_manual_start.setText("⚡ 수동 봇 시작")
        self.btn_manual_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8C7355, stop:1 #594733);
                color: #F5EFEB;
                font-weight: bold; 
                font-size: 13px; 
                padding: 11px; 
                border-radius: 4px;
                border: 1px solid #735D43;
                border-top: 1.5px solid rgba(255, 255, 255, 0.25);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A18663, stop:1 #8C7355);
            }
        """)
        
        self.lbl_guardrail.setText("진입/청산 상태:\n[비상 탈출 완료 - 대기 중]")
        self.save_shinseon_config()
        
    def trigger_close_50(self):
        if not self.bot_core.v35_engine:
            return
        self.bot_core.v35_engine.exit_reason = "수동 50% 분할 청산 명령 발동"
        self.add_log("🌓 [수동 신속 제어] BITGET 포지션 50% 시장가 청산 명령 발동...")
        asyncio.create_task(self.bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="50_PERCENT_CLOSE"))

    def reset_stoploss_ui(self):
        if hasattr(self, "bot_core") and self.bot_core and hasattr(self.bot_core, "v35_engine") and self.bot_core.v35_engine:
            self.bot_core.v35_engine.custom_stop_active = False
        if hasattr(self, "edit_stoploss_offset"):
            self.edit_stoploss_offset.setEnabled(True)
        if hasattr(self, "edit_stoploss_ratio"):
            self.edit_stoploss_ratio.setEnabled(True)
        if hasattr(self, "btn_stoploss"):
            self.btn_stoploss.setText("🛡️ 스마트 스탑 설정")
            self.btn_stoploss.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4E4944, stop:1 #35312E);
                    color: #DEBA9D;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 8px;
                    border-radius: 4px;
                    border: 1px solid #A88869;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5C5550, stop:1 #4E4944);
                }
            """)

    def trigger_stoploss_setting(self):
        if not self.bot_core.v35_engine:
            return
        
        # 1. 이미 감시 중이면 감시 해제 (토글 OFF)
        if getattr(self.bot_core.v35_engine, "custom_stop_active", False):
            self.bot_core.v35_engine.custom_stop_active = False
            self.reset_stoploss_ui()
            self.add_log("🧹 [스마트 스탑 해제] 인메모리 스마트 스탑 감시가 해제되었습니다.")
            return

        # 2. 감시 미설정 상태이면 포지션 확인 후 감시 개시 (토글 ON)
        if not self.bot_core.v35_engine.is_position_active:
            self.add_log("⚠️ [스마트 스탑 실패] 현재 열려있는 포지션이 없습니다.")
            return

        try:
            offset_val = float(self.edit_stoploss_offset.text().strip())
        except Exception:
            offset_val = 0.2
            self.edit_stoploss_offset.setText("0.2")

        try:
            ratio_val = float(self.edit_stoploss_ratio.text().strip())
        except Exception:
            ratio_val = 100.0
            self.edit_stoploss_ratio.setText("100")

        entry_price = getattr(self.bot_core.v35_engine, "entry_price", 0.0)
        entry_dir = getattr(self.bot_core.v35_engine, "entry_direction", "LONG")
        cur_price = getattr(self, "current_price", 0.0)
        if cur_price <= 0.0:
            cur_price = getattr(self, "last_price", 0.0)

        if entry_price > 0.0 and cur_price > 0.0:
            if entry_dir == "LONG":
                cur_pnl = ((cur_price - entry_price) / entry_price) * 100.0
            else:
                cur_pnl = ((entry_price - cur_price) / entry_price) * 100.0
        else:
            cur_pnl = getattr(self.bot_core.v35_engine, "last_live_pnl_pct", 0.0)

        self.bot_core.v35_engine.custom_stop_set_pnl = cur_pnl
        self.bot_core.v35_engine.custom_stop_offset_pct = offset_val
        self.bot_core.v35_engine.custom_stop_close_ratio = ratio_val
        self.bot_core.v35_engine.custom_stop_active = True

        if hasattr(self, "edit_stoploss_offset"):
            self.edit_stoploss_offset.setEnabled(False)
        if hasattr(self, "edit_stoploss_ratio"):
            self.edit_stoploss_ratio.setEnabled(False)

        if not getattr(self.bot_core.v35_engine, "is_guardrail_running", False):
            entry_dir = getattr(self.bot_core.v35_engine, "entry_direction", "LONG")
            asyncio.create_task(self.bot_core.v35_engine.manage_v35_exit_guardrail(entry_dir))

        self.btn_stoploss.setText("🟢 스마트 스탑 해제")
        self.btn_stoploss.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E4D2B, stop:1 #11331B);
                color: #00FFCC;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #00FFCC;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #27663A, stop:1 #1E4D2B);
            }
        """)

        self.add_log(f"🛡️ [스마트 스탑 설정] 현재PnL: {cur_pnl:+.2f}%, 설정오프셋: {offset_val:+.2f}%, 청산비율: {ratio_val:.0f}% 감시 개시")

    def add_price_alert(self):
        raw_text = self.edit_price_alert_target.text().strip().replace(',', '')
        if not raw_text:
            self.add_log("⚠️ [가격 알림] 목표 가격을 입력해주십시오.")
            return
        try:
            target = float(raw_text)
        except ValueError:
            self.add_log("⚠️ [가격 알림] 올바른 숫자 형식의 목표가를 입력해주십시오.")
            return

        cur_price = getattr(self, "current_price", 0.0)
        if cur_price <= 0.0:
            cur_price = getattr(self, "last_price", 0.0)

        if target > cur_price:
            dir_type = "ABOVE"
            dir_text = "상승 돌파"
        else:
            dir_type = "BELOW"
            dir_text = "하강 돌파"

        alert_item = {'target': target, 'direction': dir_type, 'dir_text': dir_text}
        self.price_alerts.append(alert_item)

        msg = f"🔔 [가격 알림 등록] 목표가 ${target:,.1f} ({dir_text} 감시 개시)"
        self.add_log(msg)
        self.send_telegram_notification(msg)
        self.update_price_alert_ui()

    def clear_price_alerts(self):
        self.price_alerts.clear()
        msg = "🔔 [가격 알림] 등록된 모든 가격 알림이 해제되었습니다."
        self.add_log(msg)
        self.update_price_alert_ui()

    def update_price_alert_ui(self):
        if not self.price_alerts:
            self.lbl_active_price_alerts.setText("🔔 감시 중인 알림 없음")
        else:
            summary_list = []
            for a in self.price_alerts:
                dir_sym = "▲" if a['direction'] == "ABOVE" else "▼"
                summary_list.append(f"${a['target']:,.1f}({dir_sym})")
            self.lbl_active_price_alerts.setText(f"🔔 감시 중 ({len(self.price_alerts)}건): " + ", ".join(summary_list))

    def update_live_ui(self, price, guardrail_stage, signal_text, liq_10s=0.0, oi_speed=0.0, ping_ms=0.0, poison_status="정상 가동 중", current_session="로딩 중", target_liq=2000000.0, target_oi=1.00, long_liq=0.0, short_liq=0.0, expected_dir="LONG"):
        # 텔레그램 원격 제어 정보 조회용 인스턴스 캐시 업데이트 (개발계획서_178)
        self.last_price = price
        self.last_current_session = current_session
        self.last_liq_10s = liq_10s
        self.last_oi_speed = oi_speed
        
        if price > 0.0:
            self.current_price = price
            self.lbl_price.setText(f"BTC/USDT 실시간 가격: {price:,.1f} USDT")

            # 실시간 목표가 가격 알림 돌파 포착 검증 (v3.65)
            if hasattr(self, 'price_alerts') and self.price_alerts:
                triggered = []
                for alert in list(self.price_alerts):
                    target = alert['target']
                    direction = alert['direction']
                    if direction == "ABOVE" and price >= target:
                        triggered.append((alert, "상승 돌파!"))
                    elif direction == "BELOW" and price <= target:
                        triggered.append((alert, "하강 돌파!"))

                for alert, dir_desc in triggered:
                    if alert in self.price_alerts:
                        self.price_alerts.remove(alert)
                    target = alert['target']
                    play_order_sound("CLEAR", getattr(self, "sound_enabled", True))
                    self.add_log(f"🔔 [가격 알림 돌파 포착] 비트코인 목표가 ${target:,.1f} {dir_desc} (현재가: ${price:,.1f})")
                    self.send_telegram_notification(f"🔔 [신선 알림] 비트코인 목표가 ${target:,.1f} {dir_desc} (현재가: ${price:,.1f})")

                if triggered:
                    self.update_price_alert_ui()
        
        # 0. KST 세션 정보 상단 라벨 갱신
        is_connected = getattr(self.bot_core, "liq_wss_connected", True)
        has_real_force = (time.time() - getattr(self.bot_core, "last_real_forceorder_time", 0.0)) <= 60.0

        if not is_connected:
            blink = (int(time.time() * 2) % 2 == 0)
            status_color = "#FF4D4D" if blink else "#888888"
            status_icon = "🚨" if blink else "⚪"
            status_msg = "바이낸스 끊김 (재접속 중)"
        elif has_real_force:
            status_color = "#00FFCC"
            status_icon = "🟢"
            status_msg = "바이낸스 1분 찐청산"
        else:
            status_color = "#D0D0D0"
            status_icon = "⚪"
            status_msg = "바이낸스 1분 청산"

        self.lbl_radar_title.setText(
            f"<b style='color:#FFFFFF; font-size: 13px;'>■ [雷達] 실시간 오더플로우 레이더</b><br>"
            f"<span style='color:{status_color}; font-size: 11px; font-weight:bold;'>{status_icon} {status_msg}</span> "
            f"<span style='color:#DEBA9D; font-size: 11px; font-weight:bold;'>({current_session})</span>"
        )
        
        # 1. 오더플로우 레이더 실시간 게이지 및 수치 갱신
        val_liq = int(min(target_liq, max(0.0, liq_10s)))
        self.bar_liq.setRange(0, int(target_liq))
        self.bar_liq.setValue(val_liq)
        
        self.bar_liq.setFormat(f"1분 누적 청산: ${liq_10s:,.0f} / ${target_liq:,.0f} (L: ${long_liq:,.0f}, S: ${short_liq:,.0f})")
        
        # [과부하 박멸 1]: QProgressBar 스타일시트 캐싱 가드 (상태 변경 시에만 1회 호출)
        current_bar_dir = "LONG" if long_liq > short_liq else "SHORT"
        if getattr(self, "_last_applied_bar_dir", None) != current_bar_dir:
            self._last_applied_bar_dir = current_bar_dir
            if current_bar_dir == "LONG":
                self.bar_liq.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid rgba(172, 90, 82, 0.45);
                        border-radius: 4px;
                        background-color: #141312;
                        text-align: center;
                        color: #F5EFEB;
                        font-family: 'Consolas';
                        font-size: 12px;
                        font-weight: bold;
                        height: 48px;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DEBA9D, stop:1 #AC5A52);
                        border-radius: 3px;
                    }
                """)
            else:
                self.bar_liq.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid rgba(82, 172, 98, 0.45);
                        border-radius: 4px;
                        background-color: #141312;
                        text-align: center;
                        color: #F5EFEB;
                        font-family: 'Consolas';
                        font-size: 12px;
                        font-weight: bold;
                        height: 48px;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DEBA9D, stop:1 #52AC62);
                        border-radius: 3px;
                    }
                """)
            
        # [과부하 박멸 2]: QLabel 힌트 스타일시트 캐싱 가드
        if getattr(self, "_last_applied_hint_dir", None) != expected_dir:
            self._last_applied_hint_dir = expected_dir
            if expected_dir == "LONG":
                self.lbl_hint.setText("[ 타점 포착 시 진입: LONG 🟢 ]")
                self.lbl_hint.setStyleSheet("""
                    QLabel {
                        background-color: rgba(82, 172, 98, 0.5);
                        border: 1px solid #52AC62;
                        border-radius: 4px;
                        color: #FFFFFF;
                        font-family: 'Consolas';
                        font-size: 12px;
                        font-weight: bold;
                    }
                """)
            else:
                self.lbl_hint.setText("[ 타점 포착 시 진입: SHORT 🔴 ]")
                self.lbl_hint.setStyleSheet("""
                    QLabel {
                        background-color: rgba(172, 90, 82, 0.5);
                        border: 1px solid #AC5A52;
                        border-radius: 4px;
                        color: #FFFFFF;
                        font-family: 'Consolas';
                        font-size: 12px;
                        font-weight: bold;
                    }
                """)
            
        # 2. 미결제약정(OI) 양방향 프로그레스바 수치 반영
        self.bar_oi.setRange(0.0, target_oi)
        self.bar_oi.setValue(oi_speed)
        self.bar_oi.setFormat(f"1분 OI 속도: {oi_speed:+.4f}% (임계: {target_oi:+.4f}%)")
            
        self.lbl_ping_ms.setText(f"패킷 레이턴시: {ping_ms:.1f}ms (상시 모니터링)")
        is_ping_high = ping_ms > 100.0
        if getattr(self, "_last_applied_ping_high", None) != is_ping_high:
            self._last_applied_ping_high = is_ping_high
            if is_ping_high:
                self.lbl_ping_ms.setStyleSheet("font-size: 11px; color: #AC5A52; font-family: 'Consolas'; font-weight: bold;")
            else:
                self.lbl_ping_ms.setStyleSheet("font-size: 11px; color: #D3C4BA; font-family: 'Consolas';")
            
        self.lbl_poison_walls.setText(f"독약 방어벽: [{poison_status}]")
        is_poison_bad = ("기각" in poison_status or "차단" in poison_status or "지연" in poison_status)
        if getattr(self, "_last_applied_poison_bad", None) != is_poison_bad:
            self._last_applied_poison_bad = is_poison_bad
            if is_poison_bad:
                self.lbl_poison_walls.setStyleSheet("font-size: 11px; color: #AC5A52; font-weight: bold;")
            else:
                self.lbl_poison_walls.setStyleSheet("font-size: 11px; color: #C5A07A; font-weight: bold;")
        
        # 3. 실시간 하트비트 스캔 로그 수술 (어떠한 PnL 수치 변화에도 1.0초 당 최대 1회만 알림 로그 송출 가드)
        now_t = time.time()
        if now_t - getattr(self, "_last_heartbeat_log_t", 0.0) >= 1.0:
            self._last_heartbeat_log_t = now_t
            clean_log_text = signal_text.replace("\n", " ")
            if signal_text != getattr(self, "last_signal_text", ""):
                self.add_log(f"레이더 피드 ➡️ {clean_log_text}")
                self.last_signal_text = signal_text
            else:
                self.add_log(f"레이더 스캔 ➡️ {clean_log_text} (청산: ${liq_10s:,.0f}, OI: {oi_speed:+.3f}%)")
            
        if "⚡ [자동 레이턴시]" in signal_text:
            # 자동 레이턴시 결과는 전용 라벨에 깔끔하게 이식
            clean_text = signal_text.replace("⚡ [자동 레이턴시] 자동측정 - ", "")
            self.lbl_auto_latency.setText(f"자동 감시: {clean_text}")
        else:
            self.lbl_guardrail.setText(f"진입/청산 상태:\n{signal_text}")
            
    def set_live_candles(self, candles_list):
        """실시간 바이낸스 15분 OHLCV 데이터 수신용 껍데기 슬롯"""
        pass

    def init_audio(self):
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            self.media_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.media_player.setAudioOutput(self.audio_output)
            self.audio_output.setVolume(1.0)
            self.sound_file_path = os.path.join(BASE_DIR, "sound", "position.mp3")
        except Exception as e:
            logger.error(f"오디오 장치 초기화 에러: {e}")
            self.media_player = None

    def play_entry_sound(self):
        if not getattr(self, "sound_enabled", True):
            return
        played = False
        if self.media_player:
            try:
                from PySide6.QtCore import QUrl
                self.media_player.setSource(QUrl.fromLocalFile(self.sound_file_path))
                self.media_player.play()
                played = True
            except Exception as e:
                self.add_log(f"⚠️ [사운드 에러] QMediaPlayer 효과음 재생 지연 ({e}) ➡️ 비프음 폴백 격발")
        if not played:
            play_order_sound("LONG", enabled=True)

    def trigger_latency_test(self):
        asyncio.create_task(self.run_manual_latency_test())

    def sync_leverage_to_exchange(self):
        if hasattr(self, "bot_core") and self.bot_core and self.bot_core.v35_engine:
            self.add_log(f"⚙️ [레버리지 동기화] BITGET 거래소 레버리지를 설정치인 {self.leverage_level}배로 동기화 조정 요청 중...")
            asyncio.create_task(self.bot_core.v35_engine.adjust_bitget_leverage(self.leverage_level))

    def trigger_manual_reload_browser(self):
        import webbrowser
        try:
            self.add_log("🌐 [비트겟 거래소] 브라우저에 거래소 화면을 띄웁니다.")
            webbrowser.open_new("https://www.bitget.com/futures/usdt/BTCUSDT")
        except Exception as e:
            self.add_log(f"⚠️ [비트겟 거래소] 브라우저 띄우기 실패: {e}")

    async def run_manual_latency_test(self):
        self.btn_latency_test.setEnabled(False)
        self.add_log("⚡ [측정 개시] 5초간 바이낸스-BITGET 물리적 시차 계측을 개시합니다...")
        
        # 127.0.0.1 로 CDP 연결 락 확보
        async with self.bot_core.cdp_lock:
            try:
                import websockets
                import json
                import time
                
                raise NotImplementedError('Playwright removed for Bitget migration') # pw = await async_playwright().start()
                browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9224", timeout=5000)
                
                target_page = None
                for context in browser.contexts:
                    for page in context.pages:
                        url = page.url
                        if "x.me" in url or "bitget" in url:
                            target_page = page
                            break
                    if target_page:
                        break
                        
                if not target_page:
                    self.add_log("❌ [측정 에러] 크롬에서 BITGET 탭을 찾지 못했습니다!")
                    await pw.stop()
                    self.btn_latency_test.setEnabled(True)
                    return
                    
                # 메모리 다이렉트 바이낸스 틱 타임스탬프 스캔 (웹소켓 버퍼 딜레이 0ms 영구 격살)
                deltas = []
                pings = []
                for i in range(5):
                    self.btn_latency_test.setText(f"측정 중 ({5-i}s)")
                    
                    # 1. 바이낸스 공식 서버 시간 초고속 REST 단발 수집 (웹소켓 딜레이/가동 여부 차단)
                    t_signal = time.time() * 1000
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get("https://api.binance.com/api/v3/time", timeout=0.8) as resp:
                                if resp.status == 200:
                                    res_time = await resp.json()
                                    t_signal = float(res_time.get("serverTime", t_signal))
                    except Exception:
                        pass
                    
                    # 2. BITGET 브라우저 evaluate fetch 핑 송출
                    start_bitget = time.time() * 1000
                    
                    # 수동 벤치용 인증 헤더 직렬화
                    curr_h = self.bot_core.bitget_headers or {}
                    if "Content-Type" not in curr_h:
                        curr_h["Content-Type"] = "application/json"
                    man_h_json = json.dumps(curr_h)
                    
                    await target_page.evaluate(f"""
                    () => fetch(window.location.origin + '/egw/private/futures/personal/info', {{
                        method: 'POST',
                        headers: {man_h_json},
                        body: '{{}}'
                    }}).then(r => r.text()).catch(e => '')
                    """)
                    t_bitget_end = time.time() * 1000
                    
                    total_delta = t_bitget_end - t_signal
                    bitget_pure_ping = t_bitget_end - start_bitget
                    if total_delta < 0:
                        total_delta = bitget_pure_ping + 10.0
                        
                    deltas.append(total_delta)
                    pings.append(bitget_pure_ping)
                    
                    verdict = "Safe" if total_delta <= 50.0 else ("Buffer" if total_delta < 200.0 else "No Edge")
                    self.add_log(f"  └ [{i+1}/5] 시차: {total_delta:.1f}ms | BITGET 핑: {bitget_pure_ping:.1f}ms | 판정: {verdict}")
                    await asyncio.sleep(1.0)
                        
                avg_delta = sum(deltas) / len(deltas)
                avg_ping = sum(pings) / len(pings)
                final_verdict = "🟢 Safe (필승 구간)" if avg_delta <= 50.0 else ("🟡 Buffer (위험 구간)" if avg_delta < 200.0 else "🔴 No Edge (진입 불가)")
                self.add_log(f"🏆 [최종 판정] 평균 총 시차: {avg_delta:.1f}ms | BITGET 핑: {avg_ping:.1f}ms -> {final_verdict}")
                
                # 수동 레이턴시 실측 결과 GUI 라벨에 출력
                verdict_short = final_verdict.split()[-1].replace('(', '').replace(')', '')
                self.lbl_latency_result.setText(f"실측 결과: {avg_delta:.1f}ms ({verdict_short})")
                
                # 24시간 계측 파일 로깅 연동
                import os
                log_dir = r"c:\Working\shinseon\docs"
                os.makedirs(log_dir, exist_ok=True)
                with open(os.path.join(log_dir, "latency_bench_log.txt"), "a", encoding="utf-8") as lf:
                    lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 수동측정 - 평균시차: {avg_delta:.1f}ms | BITGET핑: {avg_ping:.1f}ms | 판정: {final_verdict}\n")
                    
                await pw.stop()
            except Exception as e:
                if "Failed to fetch" in str(e) or "TypeError" in str(e):
                    self.add_log("⚡ [수동 레이턴시] BITGET 통신 로딩 중으로 잠시 후 다시 시도해 주십시오.")
                else:
                    self.add_log(f"❌ [측정 에러] {e}")
                self.lbl_latency_result.setText("실측 결과: 측정 에러")
                try:
                    await pw.stop()
                except:
                    pass
                    
        self.btn_latency_test.setEnabled(True)
        self.btn_latency_test.setText("⚡ 레이턴시 실측")


# ==============================================================================
# 백엔드 엔진 코어 클래스 (CCXT API 실시간 바이낸스 선물 연동)
# ==============================================================================
class ShinseonConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("⚙ 세션 / 트레이딩 핵심 설정")
        self.resize(520, 420)
        self.setModal(True)
        
        # 메인 윈도우와 정합되는 임페리얼 다크 골드 QSS 테마 적용
        self.setStyleSheet("""
            QDialog {
                background-color: #0F0E0E;
                color: #F5EFEB;
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid rgba(222, 186, 157, 0.25);
                background: #141312;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #1C1A19;
                border: 1px solid rgba(222, 186, 157, 0.15);
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                color: #D3C4BA;
                font-weight: bold;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #141312;
                border: 1px solid rgba(222, 186, 157, 0.4);
                border-bottom: none;
                color: #DEBA9D;
            }
            QLabel {
                color: #D3C4BA;
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #0A0909;
                border: 1px solid rgba(222, 186, 157, 0.3);
                border-radius: 4px;
                color: #FFFFFF;
                padding: 4px;
                font-family: 'Consolas';
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #DEBA9D;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A2624, stop:1 #1F1D1C);
                border: 1px solid rgba(222, 186, 157, 0.4);
                border-radius: 4px;
                color: #DEBA9D;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #423B37, stop:1 #322C29);
                border: 1px solid #DEBA9D;
                color: #FFFFFF;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # QTabWidget 생성
        self.tabs = QTabWidget()
        
        # 1번 탭: 세션별 설정
        self.tab_session = QWidget()
        session_layout = QGridLayout(self.tab_session)
        session_layout.setSpacing(8)
        session_layout.setContentsMargins(12, 12, 12, 12)

        # 4대 세션 헤더 (정렬 보정)
        lbl_name = QLabel("세션 구분")
        lbl_name.setAlignment(Qt.AlignCenter)
        session_layout.addWidget(lbl_name, 0, 0)

        lbl_liq = QLabel("1분 누적 청산액 ($)")
        lbl_liq.setAlignment(Qt.AlignCenter)
        session_layout.addWidget(lbl_liq, 0, 1)

        lbl_oi = QLabel("1분 OI속도 (%)")
        lbl_oi.setAlignment(Qt.AlignCenter)
        session_layout.addWidget(lbl_oi, 0, 2)

        lbl_sl = QLabel("최초 손절선 (%)")
        lbl_sl.setAlignment(Qt.AlignCenter)
        session_layout.addWidget(lbl_sl, 0, 3)

        self.session_fields = {}
        weekday_sessions = [
            ("asia", "아시아"),
            ("europe", "유럽"),
            ("us", "미국 본장"),
            ("pacific", "태평양 횡보")
        ]

        for idx, (s_key, s_name) in enumerate(weekday_sessions, start=1):
            chk_sname = QCheckBox(s_name)
            session_layout.addWidget(chk_sname, idx, 0)
            
            edit_liq = QLineEdit()
            edit_oi = QLineEdit()
            edit_sl = QLineEdit()
            
            edit_liq.setAlignment(Qt.AlignCenter)
            edit_oi.setAlignment(Qt.AlignCenter)
            edit_sl.setAlignment(Qt.AlignCenter)
            
            session_layout.addWidget(edit_liq, idx, 1)
            session_layout.addWidget(edit_oi, idx, 2)
            session_layout.addWidget(edit_sl, idx, 3)
            
            self.session_fields[s_key] = {"chk": chk_sname, "liq": edit_liq, "oi": edit_oi, "sl": edit_sl}

        # Row 5: 구분선 QFrame
        line_frame_sess = QFrame()
        line_frame_sess.setFrameShape(QFrame.HLine)
        line_frame_sess.setFrameShadow(QFrame.Sunken)
        session_layout.addWidget(line_frame_sess, 5, 0, 1, 4)

        # Row 6: QLabel("주말") 파란색 타이틀 헤더
        lbl_wknd_title_sess = QLabel("주말")
        lbl_wknd_title_sess.setStyleSheet("color: #55aaff; font-weight: bold; font-size: 14px;")
        session_layout.addWidget(lbl_wknd_title_sess, 6, 0, 1, 4)

        weekend_sessions = [
            ("weekend_asia", "주말 아시아"),
            ("weekend_europe", "주말 유럽"),
            ("weekend_us", "주말 미국 본장"),
            ("weekend_pacific", "주말 태평양")
        ]

        for idx, (s_key, s_name) in enumerate(weekend_sessions, start=7):
            chk_sname = QCheckBox(s_name)
            session_layout.addWidget(chk_sname, idx, 0)
            
            edit_liq = QLineEdit()
            edit_oi = QLineEdit()
            edit_sl = QLineEdit()
            
            edit_liq.setAlignment(Qt.AlignCenter)
            edit_oi.setAlignment(Qt.AlignCenter)
            edit_sl.setAlignment(Qt.AlignCenter)
            
            session_layout.addWidget(edit_liq, idx, 1)
            session_layout.addWidget(edit_oi, idx, 2)
            session_layout.addWidget(edit_sl, idx, 3)
            
            self.session_fields[s_key] = {"chk": chk_sname, "liq": edit_liq, "oi": edit_oi, "sl": edit_sl}

        session_layout.setRowStretch(11, 1)
        self.tabs.addTab(self.tab_session, "세션별 설정")

        # 2번 탭: 트레이딩 핵심 설정
        self.tab_trading = QWidget()
        trading_layout = QGridLayout(self.tab_trading)
        trading_layout.setSpacing(12)
        trading_layout.setContentsMargins(15, 15, 15, 15)

        trading_layout.addWidget(QLabel("포지션 레버리지 배수 (1 ~ 150배):"), 0, 0)
        self.edit_leverage = QLineEdit()
        trading_layout.addWidget(self.edit_leverage, 0, 1)

        trading_layout.addWidget(QLabel("현금 자산 대비 배팅 비중 (%):"), 1, 0)
        self.edit_betting = QLineEdit()
        self.edit_betting.setReadOnly(True)
        self.edit_betting.setStyleSheet("background-color: #1A1817; color: #DEBA9D; border: 1px solid rgba(222, 186, 157, 0.15);")
        trading_layout.addWidget(self.edit_betting, 1, 1)

        trading_layout.addWidget(QLabel("1차 매수 비중 (%):"), 2, 0)
        self.edit_split_entry_1 = QLineEdit()
        trading_layout.addWidget(self.edit_split_entry_1, 2, 1)

        trading_layout.addWidget(QLabel("2차 매수 비중 (%):"), 3, 0)
        self.edit_split_entry_2 = QLineEdit()
        trading_layout.addWidget(self.edit_split_entry_2, 3, 1)

        trading_layout.addWidget(QLabel("2차 진입 하락폭 (1차 대비 %):"), 4, 0)
        self.edit_split_trigger = QLineEdit()
        trading_layout.addWidget(self.edit_split_trigger, 4, 1)

        trading_layout.addWidget(QLabel("3차 매수 비중 (%):"), 5, 0)
        self.edit_split_entry_3 = QLineEdit()
        trading_layout.addWidget(self.edit_split_entry_3, 5, 1)

        trading_layout.addWidget(QLabel("3차 진입 하락폭 (1차 대비 %):"), 6, 0)
        self.edit_split_trigger_3 = QLineEdit()
        trading_layout.addWidget(self.edit_split_trigger_3, 6, 1)

        trading_layout.addWidget(QLabel("추가 매수 후 진입 제한 시간 (초):"), 7, 0)
        self.edit_split_cooldown = QLineEdit()
        trading_layout.addWidget(self.edit_split_cooldown, 7, 1)

        trading_layout.addWidget(QLabel("손절 후 진입 제한 시간 (초):"), 8, 0)
        self.edit_cooldown = QLineEdit()
        trading_layout.addWidget(self.edit_cooldown, 8, 1)
        
        trading_layout.addWidget(QLabel("익절 후 진입 제한 시간 (초):"), 9, 0)
        self.edit_profit_cooldown = QLineEdit()
        trading_layout.addWidget(self.edit_profit_cooldown, 9, 1)
        
        # 실시간 비중 자동 계산 및 반영 커넥션
        self.edit_split_entry_1.textChanged.connect(self.update_total_betting_ratio)
        self.edit_split_entry_2.textChanged.connect(self.update_total_betting_ratio)
        self.edit_split_entry_3.textChanged.connect(self.update_total_betting_ratio)
        
        # 하단 여백 채우기
        trading_layout.setRowStretch(10, 1)

        self.tabs.addTab(self.tab_trading, "트레이딩 핵심 설정")

        # 3번 탭: 알림 설정 (개발계획서_178, 기획서_217 개혁)
        self.tab_telegram = QWidget()
        tab_telegram_main_layout = QVBoxLayout(self.tab_telegram)
        tab_telegram_main_layout.setSpacing(15)
        tab_telegram_main_layout.setContentsMargins(15, 15, 15, 15)

        # 1. 텔레그램 설정 그룹박스
        grp_telegram = QGroupBox("📱 텔레그램 원격 제어 및 알림 설정")
        grp_telegram.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(222, 186, 157, 0.4);
                border-radius: 6px;
                margin-top: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: bold;
                color: #DEBA9D;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
            }
        """)
        telegram_layout = QGridLayout(grp_telegram)
        telegram_layout.setSpacing(12)
        telegram_layout.setContentsMargins(12, 20, 12, 15)
        
        self.chk_telegram_enabled = QCheckBox("텔레그램 알림 및 원격 제어 활성화")
        self.chk_telegram_enabled.setStyleSheet("""
            QCheckBox {
                font-size: 11px;
                font-weight: bold;
                color: #DEBA9D;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid rgba(222, 186, 157, 0.5);
                background-color: #141312;
                border-radius: 3px;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #DEBA9D;
            }
            QCheckBox::indicator:checked {
                background-color: #DEBA9D;
                border: 1px solid #DEBA9D;
            }
        """)
        telegram_layout.addWidget(self.chk_telegram_enabled, 0, 0, 1, 2)
        
        telegram_layout.addWidget(QLabel("봇 토큰 (Bot Token):"), 1, 0)
        self.edit_telegram_token = QLineEdit()
        self.edit_telegram_token.setPlaceholderText("봇 토큰을 입력하십시오 (예: 123456789:ABCdef...)")
        telegram_layout.addWidget(self.edit_telegram_token, 1, 1)
        
        telegram_layout.addWidget(QLabel("챗 ID (Chat ID):"), 2, 0)
        self.edit_telegram_chat_id = QLineEdit()
        self.edit_telegram_chat_id.setPlaceholderText("채팅 ID를 입력하십시오 (예: 987654321)")
        telegram_layout.addWidget(self.edit_telegram_chat_id, 2, 1)
        
        tab_telegram_main_layout.addWidget(grp_telegram)

        # 2. 사운드 및 효과음 설정 그룹박스 (텔레그램 하단 독립 배치)
        grp_sound = QGroupBox("🔊 사운드 및 효과음 설정")
        grp_sound.setStyleSheet(grp_telegram.styleSheet())
        sound_layout = QVBoxLayout(grp_sound)
        sound_layout.setSpacing(10)
        sound_layout.setContentsMargins(12, 20, 12, 15)

        self.chk_sound_enabled = QCheckBox("🔊 주문/진입/청산 사운드 효과음 출력 활성화")
        self.chk_sound_enabled.setStyleSheet(self.chk_telegram_enabled.styleSheet())
        sound_layout.addWidget(self.chk_sound_enabled)

        tab_telegram_main_layout.addWidget(grp_sound)
        tab_telegram_main_layout.addStretch(1)

        self.tabs.addTab(self.tab_telegram, "알림 설정")

        # 4번 탭: 가드레일 설정
        self.tab_guardrail = QWidget()
        guardrail_layout = QGridLayout(self.tab_guardrail)
        guardrail_layout.setSpacing(12)
        guardrail_layout.setContentsMargins(15, 15, 15, 15)
        
        # 세션별 가드레일 설정 헤더 (Row 0)
        lbl_sess = QLabel("세션")
        lbl_sess.setAlignment(Qt.AlignCenter)
        lbl_trig = QLabel("분할익절 임계값(%)")
        lbl_trig.setAlignment(Qt.AlignCenter)
        lbl_grd = QLabel("본전/버퍼 가드(%)")
        lbl_grd.setAlignment(Qt.AlignCenter)
        lbl_en = QLabel("분할익절 가동")
        lbl_en.setAlignment(Qt.AlignCenter)
        guardrail_layout.addWidget(lbl_sess, 0, 0)
        guardrail_layout.addWidget(lbl_trig, 0, 1)
        guardrail_layout.addWidget(lbl_grd, 0, 2)
        guardrail_layout.addWidget(lbl_en, 0, 3)
        
        self.edit_guard_trigger = {}
        self.edit_guard_limit = {}
        self.chk_guard_enabled = {}
        
        weekday_guardrails = [
            ("ASIA", "아시아"),
            ("LONDON", "유럽(런던)"),
            ("NY", "미국 본장"),
            ("PACIFIC", "태평양")
        ]
        for idx, (s_key, s_name) in enumerate(weekday_guardrails, start=1):
            lbl_sname = QLabel(s_name)
            lbl_sname.setAlignment(Qt.AlignCenter)
            guardrail_layout.addWidget(lbl_sname, idx, 0)
            
            e_trig = QLineEdit()
            e_trig.setAlignment(Qt.AlignCenter)
            guardrail_layout.addWidget(e_trig, idx, 1)
            self.edit_guard_trigger[s_key] = e_trig
            
            e_limit = QLineEdit()
            e_limit.setAlignment(Qt.AlignCenter)
            guardrail_layout.addWidget(e_limit, idx, 2)
            self.edit_guard_limit[s_key] = e_limit

            c_en = QCheckBox()
            c_en.setStyleSheet("QCheckBox::indicator { width: 24px; height: 24px; }")
            layout_en = QHBoxLayout()
            layout_en.setAlignment(Qt.AlignCenter)
            layout_en.addWidget(c_en)
            w_en = QWidget()
            w_en.setLayout(layout_en)
            guardrail_layout.addWidget(w_en, idx, 3)
            self.chk_guard_enabled[s_key] = c_en

        # Row 5: 구분선 QFrame
        line_frame_grd = QFrame()
        line_frame_grd.setFrameShape(QFrame.HLine)
        line_frame_grd.setFrameShadow(QFrame.Sunken)
        guardrail_layout.addWidget(line_frame_grd, 5, 0, 1, 4)

        # Row 6: QLabel("주말") 파란색 타이틀 헤더
        lbl_wknd_title_grd = QLabel("주말")
        lbl_wknd_title_grd.setStyleSheet("color: #55aaff; font-weight: bold; font-size: 14px;")
        guardrail_layout.addWidget(lbl_wknd_title_grd, 6, 0, 1, 4)

        weekend_guardrails = [
            ("WEEKEND_ASIA", "주말 아시아"),
            ("WEEKEND_LONDON", "주말 유럽(런던)"),
            ("WEEKEND_NY", "주말 미국 본장"),
            ("WEEKEND_PACIFIC", "주말 태평양")
        ]
        for idx, (s_key, s_name) in enumerate(weekend_guardrails, start=7):
            lbl_sname = QLabel(s_name)
            lbl_sname.setAlignment(Qt.AlignCenter)
            guardrail_layout.addWidget(lbl_sname, idx, 0)
            
            e_trig = QLineEdit()
            e_trig.setAlignment(Qt.AlignCenter)
            guardrail_layout.addWidget(e_trig, idx, 1)
            self.edit_guard_trigger[s_key] = e_trig
            
            e_limit = QLineEdit()
            e_limit.setAlignment(Qt.AlignCenter)
            guardrail_layout.addWidget(e_limit, idx, 2)
            self.edit_guard_limit[s_key] = e_limit

            c_en = QCheckBox()
            c_en.setStyleSheet("QCheckBox::indicator { width: 24px; height: 24px; }")
            layout_en = QHBoxLayout()
            layout_en.setAlignment(Qt.AlignCenter)
            layout_en.addWidget(c_en)
            w_en = QWidget()
            w_en.setLayout(layout_en)
            guardrail_layout.addWidget(w_en, idx, 3)
            self.chk_guard_enabled[s_key] = c_en

        guardrail_layout.addWidget(QLabel("분할 익절 청산 비율 (%):"), 11, 0)
        self.edit_half_exit_ratio = QLineEdit()
        guardrail_layout.addWidget(self.edit_half_exit_ratio, 11, 1, 1, 2)
        
        # 불타기
        self.chk_pyramiding_enabled = QCheckBox("추세 추종 불타기(Pyramiding) 가동")
        self.chk_pyramiding_enabled.setStyleSheet(self.chk_telegram_enabled.styleSheet())
        guardrail_layout.addWidget(self.chk_pyramiding_enabled, 12, 0, 1, 2)
        
        self.edit_pyramiding_ratio = QLineEdit()
        self.edit_pyramiding_ratio.setPlaceholderText("비중% (예: 30.0)")
        guardrail_layout.addWidget(self.edit_pyramiding_ratio, 12, 2)
        
        guardrail_layout.setRowStretch(13, 1)
        self.tabs.addTab(self.tab_guardrail, "가드레일 설정")

        main_layout.addWidget(self.tabs)

        # 하단 버튼부 (적용 및 저장, 기본값 복원, 취소)
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("적용 및 저장")
        self.btn_restore = QPushButton("기본값 복원")
        self.btn_cancel = QPushButton("취소")

        btn_layout.addWidget(self.btn_restore)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

        # 이벤트 연결
        self.btn_apply.clicked.connect(self.apply_and_save)
        self.btn_restore.clicked.connect(self.restore_defaults)
        self.btn_cancel.clicked.connect(self.reject)

        # 현재 데이터 필드에 채우기
        self.load_values()

    def load_values(self):
        if not self.parent:
            return
        
        # 세션별 데이터 로드
        for s_key, fields in self.session_fields.items():
            data = self.parent.session_thresholds.get(s_key, {"liq": 100000.0, "oi": 0.05, "sl": -1.3, "enabled": True})
            fields["chk"].setChecked(data.get("enabled", True))
            fields["liq"].setText(f"{int(data['liq']):,}")
            fields["oi"].setText(f"{data['oi']:.4f}")
            fields["sl"].setText(f"{data['sl']:.1f}")

        # 트레이딩 핵심 데이터 로드
        self.edit_leverage.setText(str(self.parent.leverage_level))
        self.edit_split_entry_1.setText(f"{self.parent.split_entry_1_ratio:.1f}")
        self.edit_split_entry_2.setText(f"{self.parent.split_entry_2_ratio:.1f}")
        self.edit_split_trigger.setText(f"{self.parent.split_entry_2_trigger_pct:.2f}")
        self.edit_split_entry_3.setText(f"{self.parent.split_entry_3_ratio:.1f}")
        self.edit_split_trigger_3.setText(f"{self.parent.split_entry_3_trigger_pct:.2f}")
        self.edit_split_cooldown.setText(f"{self.parent.split_cooldown_seconds:.1f}")
        self.edit_cooldown.setText(f"{self.parent.cooldown_seconds:.1f}")
        self.edit_profit_cooldown.setText(f"{self.parent.profit_cooldown_seconds:.1f}")
        self.update_total_betting_ratio()

        # 텔레그램 및 알림 사운드 데이터 로드 (개발계획서_178)
        self.chk_telegram_enabled.setChecked(self.parent.telegram_enabled)
        self.chk_sound_enabled.setChecked(getattr(self.parent, "sound_enabled", True))
        self.edit_telegram_token.setText(self.parent.telegram_token)
        self.edit_telegram_chat_id.setText(self.parent.telegram_chat_id)

        self.edit_half_exit_ratio.setText(f"{self.parent.half_exit_close_ratio:.1f}")
        
        all_guardrail_keys = ["ASIA", "LONDON", "NY", "PACIFIC", "WEEKEND_ASIA", "WEEKEND_LONDON", "WEEKEND_NY", "WEEKEND_PACIFIC"]
        for s_key in all_guardrail_keys:
            data = getattr(self.parent, "session_guardrails", {}).get(s_key, {"trigger": 0.5, "guard": 0.0, "enabled": True})
            self.edit_guard_trigger[s_key].setText(f"{data['trigger']:.2f}")
            self.edit_guard_limit[s_key].setText(f"{data['guard']:.2f}")
            self.chk_guard_enabled[s_key].setChecked(data.get('enabled', True))
            
        self.chk_pyramiding_enabled.setChecked(getattr(self.parent, "pyramiding_enabled", True))
        self.edit_pyramiding_ratio.setText(f"{getattr(self.parent, 'pyramiding_ratio', 30.0):.1f}")


    def apply_and_save(self):
        if not self.parent:
            self.accept()
            return
            
        try:
            # 세션별 값 파싱 및 검증
            new_thresholds = {}
            for s_key, fields in self.session_fields.items():
                liq_val = float(fields["liq"].text().replace(",", "").strip())
                oi_val = float(fields["oi"].text().strip())
                sl_val = float(fields["sl"].text().strip())
                chk_val = fields["chk"].isChecked()
                new_thresholds[s_key] = {"liq": liq_val, "oi": oi_val, "sl": sl_val, "enabled": chk_val}
            
            # 레버리지 및 배팅비중 파싱
            lev_val = int(self.edit_leverage.text().strip())
            bet_val = float(self.edit_betting.text().strip())
            split_entry_1_val = float(self.edit_split_entry_1.text().strip())
            split_entry_2_val = float(self.edit_split_entry_2.text().strip())
            split_trigger_val = float(self.edit_split_trigger.text().strip())
            split_entry_3_val = float(self.edit_split_entry_3.text().strip())
            split_trigger_3_val = float(self.edit_split_trigger_3.text().strip())
            split_cooldown_val = float(self.edit_split_cooldown.text().strip())
            cooldown_val = float(self.edit_cooldown.text().strip())
            profit_cooldown_val = float(self.edit_profit_cooldown.text().strip())
            
            # 범위 제한 (레버리지는 1~150배)
            if not (1 <= lev_val <= 150):
                raise ValueError("레버리지는 1배에서 최대 150배 범위여야 합니다.")
                
            # 부모 윈도우에 반영
            self.parent.session_thresholds = new_thresholds
            self.parent.leverage_level = lev_val
            self.parent.betting_ratio = bet_val
            self.parent.split_entry_1_ratio = split_entry_1_val
            self.parent.split_entry_2_ratio = split_entry_2_val
            self.parent.split_entry_2_trigger_pct = split_trigger_val
            self.parent.split_entry_3_ratio = split_entry_3_val
            self.parent.split_entry_3_trigger_pct = split_trigger_3_val
            self.parent.split_cooldown_seconds = split_cooldown_val
            self.parent.cooldown_seconds = cooldown_val
            self.parent.profit_cooldown_seconds = profit_cooldown_val
            
            # 텔레그램 및 알림 사운드 설정 반영 (개발계획서_178)
            self.parent.telegram_enabled = self.chk_telegram_enabled.isChecked()
            self.parent.sound_enabled = self.chk_sound_enabled.isChecked()
            self.parent.telegram_token = self.edit_telegram_token.text().strip()
            self.parent.telegram_chat_id = self.edit_telegram_chat_id.text().strip()

            half_exit_ratio_val = float(self.edit_half_exit_ratio.text().strip())
            
            new_guardrails = {}
            all_guardrail_keys = ["ASIA", "LONDON", "NY", "PACIFIC", "WEEKEND_ASIA", "WEEKEND_LONDON", "WEEKEND_NY", "WEEKEND_PACIFIC"]
            for s_key in all_guardrail_keys:
                trig_val = float(self.edit_guard_trigger[s_key].text().strip())
                grd_val = float(self.edit_guard_limit[s_key].text().strip())
                en_val = self.chk_guard_enabled[s_key].isChecked()
                new_guardrails[s_key] = {"trigger": trig_val, "guard": grd_val, "enabled": en_val}
            
            pyra_enabled = self.chk_pyramiding_enabled.isChecked()
            pyra_ratio = float(self.edit_pyramiding_ratio.text().strip())
            
            self.parent.half_exit_close_ratio = half_exit_ratio_val
            self.parent.session_guardrails = new_guardrails
            self.parent.pyramiding_enabled = pyra_enabled
            self.parent.pyramiding_ratio = pyra_ratio
            
            # 설정 파일 저장
            self.parent.save_shinseon_config()
            self.parent.add_log("⚙ [설정 변경] 세션별 임계치 및 트레이딩 핵심 파라미터 설정을 적용 및 저장했습니다.")
            self.parent.sync_leverage_to_exchange()
            self.accept()
            QApplication.processEvents()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "입력 에러", f"설정 값 파싱 실패: {e}\n모든 필드에 정확한 숫자를 입력해 주십시오.")

    def update_total_betting_ratio(self):
        try:
            val1 = float(self.edit_split_entry_1.text().strip() or 0.0)
            val2 = float(self.edit_split_entry_2.text().strip() or 0.0)
            val3 = float(self.edit_split_entry_3.text().strip() or 0.0)
            self.edit_betting.setText(f"{val1 + val2 + val3:.1f}")
        except ValueError:
            self.edit_betting.setText("0.0")

    def restore_defaults(self):
        # 하드코딩된 기본값 복원 (UI 필드만 채우고 적용 및 저장은 명시적으로 누르도록 함)
        default_thresholds = {
            "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
            "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
            "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
            "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True},
            "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
            "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
            "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
            "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True}
        }
        
        for s_key, fields in self.session_fields.items():
            data = default_thresholds[s_key]
            fields["chk"].setChecked(data.get("enabled", True))
            fields["liq"].setText(f"{int(data['liq']):,}")
            fields["oi"].setText(f"{data['oi']:.4f}")
            fields["sl"].setText(f"{data['sl']:.1f}")

        self.edit_leverage.setText("30")
        self.edit_half_exit_ratio.setText("50.0")
        
        default_guardrails = {
            "ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
            "LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
            "NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
            "PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True},
            "WEEKEND_ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
            "WEEKEND_LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
            "WEEKEND_NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
            "WEEKEND_PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True}
        }
        all_guardrail_keys = ["ASIA", "LONDON", "NY", "PACIFIC", "WEEKEND_ASIA", "WEEKEND_LONDON", "WEEKEND_NY", "WEEKEND_PACIFIC"]
        for s_key in all_guardrail_keys:
            self.edit_guard_trigger[s_key].setText(f"{default_guardrails[s_key]['trigger']:.2f}")
            self.edit_guard_limit[s_key].setText(f"{default_guardrails[s_key]['guard']:.2f}")
            self.chk_guard_enabled[s_key].setChecked(default_guardrails[s_key]['enabled'])
            
        self.chk_pyramiding_enabled.setChecked(True)
        self.edit_pyramiding_ratio.setText("30.0")
        
        self.edit_betting.setText("1200.0")
        self.edit_split_entry_1.setText("800.0")
        self.edit_split_entry_2.setText("400.0")
        self.edit_split_trigger.setText("-0.3")
        self.edit_split_entry_3.setText("0.0")
        self.edit_split_trigger_3.setText("0.0")
        self.edit_split_cooldown.setText("900.0")
        self.edit_cooldown.setText("300.0")
        self.edit_profit_cooldown.setText("15.0")
        
        # 텔레그램 설정 초기화 (개발계획서_178)
        self.chk_telegram_enabled.setChecked(True)
        self.edit_telegram_token.setText("8890976392:AAFkGFrep1b9N9P_EQpJY-yNYaMLcd2kEZk")
        self.edit_telegram_chat_id.setText("8279848058")
        
        if self.parent:
            self.parent.add_log("⚙ [설정 복원] 입력 필드 값을 황실 기본값으로 채웠습니다. 적용하려면 [적용 및 저장]을 누르십시오.")


# ==============================================================================
# 라이선스 인증 도구 및 다이얼로그 (개발계획서_179)
# ==============================================================================
def get_hardware_uuid():
    try:
        output = subprocess.check_output(
            ["wmic", "csproduct", "get", "uuid"],
            creationflags=0x08000000,
            stderr=subprocess.DEVNULL
        )
        lines = output.decode("utf-8", errors="ignore").splitlines()
        for line in lines:
            line = line.strip()
            if line and "uuid" not in line.lower() and line != "00000000-0000-0000-0000-000000000000":
                return line
        raise Exception("유효한 UUID를 획득하지 못했습니다.")
    except Exception:
        try:
            mac = uuid.getnode()
            mac_str = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
            return f"MAC-{mac_str}"
        except Exception:
            return "UNKNOWN-HARDWARE-ID"

def check_license_online(hw_id):
    try:
        req = urllib.request.Request(LICENSE_URL, headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=5.0) as response:
            license_bytes = response.read()
            
        license_data = json.loads(license_bytes.decode('utf-8'))
        
        for user in license_data:
            uuid_val = user.get("uuid", "").strip()
            status_val = user.get("status", "").strip().upper()
            name_val = user.get("name", "").strip()
            
            if uuid_val.lower() == hw_id.lower():
                if status_val in ['ACTIVE', 'Y', '승인', 'YES', 'TRUE']:
                    return True, f"승인 완료 (사용자: {name_val})"
                else:
                    return False, f"라이선스 비활성화 상태 (상태: {status_val})"
                    
        return False, "등록되지 않은 기기 ID입니다."
    except Exception as e:
        try:
            local_lic_path = os.path.join(BASE_DIR, "docs", "license.json")
            if os.path.exists(local_lic_path):
                with open(local_lic_path, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                for user in local_data:
                    uuid_val = user.get("uuid", "").strip()
                    status_val = user.get("status", "").strip().upper()
                    name_val = user.get("name", "").strip()
                    if uuid_val.lower() == hw_id.lower() and status_val in ['ACTIVE', 'Y', '승인', 'YES', 'TRUE']:
                        return True, f"승인 완료 (로컬 2중 방어선: {name_val})"
        except Exception:
            pass
        return False, f"라이선스 서버 연결 실패 ({e})"

class ShinseonLicenseDialog(QDialog):
    def __init__(self, hw_id, reason, parent=None):
        super().__init__(parent)
        self.hw_id = hw_id
        self.reason = reason
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("🔒 신선 마스터 - 라이선스 인증 필요")
        self.resize(450, 230)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #0F0E0E;
                color: #F5EFEB;
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #D3C4BA;
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #0A0909;
                border: 1px solid rgba(222, 186, 157, 0.4);
                border-radius: 4px;
                color: #FFFFFF;
                padding: 6px;
                font-family: 'Consolas';
                font-size: 12px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A2624, stop:1 #1F1D1C);
                border: 1px solid rgba(222, 186, 157, 0.4);
                border-radius: 4px;
                color: #DEBA9D;
                font-weight: bold;
                font-size: 11px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #423B37, stop:1 #322C29);
                border: 1px solid #DEBA9D;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        info_label = QLabel("⚠️ 프로그램 승인이 만료되었거나 승인되지 않은 기기입니다.\n"
                            f"사유: {self.reason}\n\n"
                            "아래의 기기 고유 ID(Hardware UUID)를 복사하여\n"
                            "대표님께 전달 후 승인을 요청해 주시기 바랍니다.")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        self.edit_hw_id = QLineEdit(self.hw_id)
        self.edit_hw_id.setReadOnly(True)
        self.edit_hw_id.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.edit_hw_id)

        btn_layout = QHBoxLayout()
        self.btn_copy = QPushButton("📋 기기 ID 복사")
        self.btn_exit = QPushButton("종료")
        
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_exit)
        layout.addLayout(btn_layout)

        self.btn_copy.clicked.connect(self.copy_hw_id)
        self.btn_exit.clicked.connect(self.reject)

    def copy_hw_id(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hw_id)
        self.btn_copy.setText("✔ 복사 완료!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 기기 ID 복사"))

# ==============================================================================
# 애플리케이션 진입점 (qasync 이벤트 루프 바인딩)
# ==============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    class DummyBot:
        v35_engine = None
        
    dashboard = ShinseonDashboard(DummyBot())
    dashboard.show()
    
    loop.create_task(dashboard.connect_websocket())
    
    with loop:
        loop.run_forever()
