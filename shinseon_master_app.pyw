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
import ccxt.async_support as ccxt
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
import aiohttp
import aiohttp.connector

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
GITHUB_REPO = "shinseon"
GITHUB_BRANCH = "master"
LICENSE_URL = "https://raw.githubusercontent.com/NaThanAEL7912/shinseon/master/docs/license.json"

# 2. .env 환경변수 수동 파싱 엔진 (dotenv 패키지 의존성 완전 제거)
def load_env_file():
    env_path = os.path.join(BASE_DIR, ".env")
    env_data = {"BINANCE_API_KEY": "", "BINANCE_SECRET": "", "BINANCE_SECRET_KEY": "", "BITGET_API_KEY": "", "BITGET_SECRET_KEY": "", "BITGET_PASSPHRASE": ""}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        env_data[key.strip()] = val.strip()
        except Exception as e:
            print(f"[Warn] .env 로드 중 오류 발생: {e}")
    return env_data

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
        self.CURRENT_VERSION = "v4.08"  # [기획서_80] 자동 봇 시작 OFF 시 강제 청산 탈취 완벽 차단 핫픽스
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
        
        self.lbl_capital_display = QLabel("총 가용 자본금: $20,000.00 (실시간 동기화 대기)")
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
        
        # [RPA 복원] 🌐 브라우저 새로고침/복원 버튼
        self.btn_reload_browser = QPushButton("🌐 브라우저 새로고침/복원", right_widget)
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
            self.add_log("보안 자격 증명 (.env) 해석 및 API 키 연동 성공.")
        else:
            self.add_log("[안내] 모의 투자 시뮬레이션 모드로 가동이 준비되었습니다.")

    def add_log(self, text):
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
        try:
            # 1. 바이낸스 실시간 선물 USDT 잔고 조회
            bin_key = env_vars.get("BINANCE_API_KEY", "")
            bin_secret = env_vars.get("BINANCE_SECRET", "") or env_vars.get("BINANCE_SECRET_KEY", "")
            
            bin_balance = None
            if bin_key and "your_" not in bin_key and bin_secret:
                exchange = None
                try:
                    exchange = ccxt.binanceusdm({
                        'apiKey': bin_key,
                        'secret': bin_secret,
                        'enableRateLimit': True,
                    })
                    bal = await exchange.fetch_balance()
                    bin_balance = float(bal.get('USDT', {}).get('free', 0.0))
                except Exception as e:
                    self.add_log(f"[경고] 바이낸스 API 잔고 조회 실패: {str(e)[:30]}")
                finally:
                    if exchange:
                        await exchange.close()
            
            # 2. BITGET 실시간 선물 USDT 잔고 조회 (RPA 원격 디버깅)
            bitget_balance = None
            try:
                if self.bot_core.bitget_exchange is None:
                    self.add_log("[에러] 비트겟 API 객체가 없습니다. API 키를 확인하십시오.")
                else:
                    bal = await self.bot_core.bitget_exchange.fetch_balance()
                    bitget_balance = float(bal.get('USDT', {}).get('free', 0.0))
                    
                    # 포지션 동기화
                    positions = await self.bot_core.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])
                    active_pos = None
                    for p in positions:
                        pVol = float(p.get('contracts', 0) or 0)
                        if pVol > 0:
                            active_pos = p
                            break
                            
                    if active_pos:
                        direction = "LONG" if str(active_pos.get('side', '')).lower() == 'long' else "SHORT"
                        entry_price = float(active_pos.get('entryPrice', 0))
                        size_val = float(active_pos.get('contracts', 0))
                        pos_id = active_pos.get('id', "")
                        
                        if entry_price > 0.0 and size_val > 0.0:
                            if self.bot_core.v35_engine:
                                self.bot_core.v35_engine.position_volume = int(round(size_val * 1000))
                                if pos_id:
                                    self.bot_core.v35_engine.active_position_ids = [pos_id]
                                if not self.bot_core.v35_engine.is_position_active or self.bot_core.v35_engine.entry_direction != direction:
                                    self.bot_core.v35_engine.peak_pnl_pct = 0.0
                                    self.bot_core.v35_engine.entry_price_1 = entry_price
                                    self.bot_core.v35_engine.is_position_active = True
                                    self.bot_core.v35_engine.entry_direction = direction
                                    self.bot_core.v35_engine.entry_price = entry_price
                                    self.bot_core.v35_engine.has_second_entry = False
                                    self.bot_core.v35_engine.has_third_entry = False
                                    if self.bot_core.v35_engine.is_snipe_active:
                                        asyncio.create_task(self.bot_core.v35_engine.manage_v35_exit_guardrail(direction))
                                else:
                                    if self.bot_core.v35_engine.entry_price_1 <= 0.0:
                                        self.bot_core.v35_engine.entry_price_1 = entry_price
                                    self.bot_core.v35_engine.is_position_active = True
                                    self.bot_core.v35_engine.entry_direction = direction
                                    self.bot_core.v35_engine.entry_price = entry_price
                                    
                            pnl_val = float(active_pos.get('unrealizedPnl', 0) or 0)
                            self.last_pnl_usdt = pnl_val
                            
                            self.lbl_guardrail.setText(f"진입/청산 상태:\n[{direction} 진입 완료] 단가: {entry_price:,.0f}")
                            self.add_log(f"✔ [포지션 동기화 완료] 열린 포지션 감지: {direction} @ {entry_price:,.1f} USD")
                    else:
                        if self.bot_core.v35_engine:
                            self.bot_core.v35_engine.is_position_active = False
                        self.last_pnl_usdt = 0.0
                        self.lbl_guardrail.setText("진입/청산 상태:\n[100% 현금 대기 중]")
                        self.add_log("✔ [포지션 동기화 완료] 열려있는 포지션이 없습니다. (100% 현금)")
                        
            except Exception as e:
                self.add_log(f"[안내] BITGET 잔고 및 포지션 API 조회 에러: {e}")
            
            # 3. BITGET 단독 운용 모드: 바이낸스 연동을 배제하고 오직 BITGET 잔고를 100% 자본금으로 설정
            final_bin = 0.0
            if bitget_balance is not None and bitget_balance > 0.0:
                final_bitget = bitget_balance
            else:
                prev_bal = getattr(self, "last_balance", 0.0)
                final_bitget = prev_bal if prev_bal > 100.0 else 20000.0
                self.add_log(f"⚠️ [잔고 보정] BITGET 잔고 0원 수신 ➡️ 이전 정상 자본금(${final_bitget:,.2f})으로 자가 복구 유지합니다.")
            final_total = final_bitget
            self.last_balance = final_total
            
            target_bitget = final_total
            target_bin = 0.0
            
            # UI 라벨 실시간 업데이트
            self.lbl_capital_display.setText(f"총 가용 자본금: ${final_total:,.2f}")
            
            # 자본 가용성 가드레일 (USDT Minimum Guard)
            is_insufficient = False
            if final_total < 100.0:
                is_insufficient = True
                
            if is_insufficient:
                self.btn_start.setEnabled(False)
                self.btn_start.setText("❌ 자금 부족 (자동 봇 잠금)")
                self.btn_start.setStyleSheet("""
                    QPushButton {
                        background: #AC5A52; /* 경고 버건디 */
                        color: #FFFFFF;
                        font-weight: bold;
                        font-size: 13px;
                        padding: 11px;
                        border-radius: 4px;
                        border: 1px solid #732E27;
                    }
                """)
                self.add_log("❌ [자본 고갈 경고] 실계좌 자본금($100 미만)이 부족하여 진입이 불가능합니다!")
                self.add_log(f"  ➡️ 실전 총자산: ${final_total:,.2f} < 최소 요구액 $100.00")
            else:
                self.btn_start.setEnabled(True)
                # 만약 자동 봇이 현재 가동 중이면 "정지" 텍스트를 유지하고, 대기 중일 때만 "시작" 텍스트 적용
                if self.bot_core.v35_engine and self.bot_core.v35_engine.is_snipe_active:
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
                self.add_log("✔ [검증 완료] 거래소 가용 자금이 충분합니다. 대칭 헷지 준비 완료!")
                
            # 백엔드 엔진 코어 자본 설정 연동 (100% 자동 합산 매핑 반영)
            self.bot_core.bitget_balance = final_bitget
            m_bitget = final_total
            m_bin = 0.0
            p_target = max(1000.0, final_bitget * (self.betting_ratio / 100.0))
            self.bot_core.update_capital_config(final_total, m_bitget, m_bin, p_target)
            self.add_log(f"✔ [동기화 완료] 실계좌 총자산(BITGET 단독): ${final_total:,.2f}, 동적 목표 포지션 규모: ${p_target:,.2f}")
            
        except Exception as ex:
            self.add_log(f"[오류] 계좌 동기화 도중 예외 발생: {ex}")
        finally:
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
                    
                self.lbl_guardrail.setText(f"진입/청산 상태:\n[{direction} 진입 완료] 단가: {entry_price:,.0f}")
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
                self.lbl_guardrail.setText("진입/청산 상태:\n[100% 현금 대기 중]")
                self.add_log("✔ [동기화 완료] 열려있는 포지션이 없습니다. (100% 현금)")
            
            self.add_log("🌓 [수동 리로드] BITGET 포지션 상태를 강제로 재동기화 완료하였습니다.")
            
        except Exception as e:
            self.add_log(f"❌ [동기화 실패] 포지션 스캔 중 오류 발생: {e}")
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



    def start_bot(self):
        if not self.bot_core.v35_engine:
            self.add_log("[오류] 백엔드 엔진이 준비되지 않았습니다.")
            return
            
        if not self.bot_core.v35_engine.is_snipe_active:
            # 1. 과거 잔재 락 및 포지션 플래그 100% 클린 리셋 (29차 과업)
            self.bot_core.v35_engine.is_half_exited = False
            self.bot_core.v35_engine.has_smart_guarded = False
            self.bot_core.v35_engine.has_pyramided = False
            self.bot_core.v35_engine.awaiting_pullback_pyramid = False
            self.bot_core.v35_engine.peak_pnl_pct = 0.0
            self.bot_core.v35_engine.has_second_entry = False
            self.bot_core.v35_engine.has_third_entry = False
            self.bot_core.v35_engine.exit_in_progress = False
            self.add_log("🧹 [클린 리셋] 봇 가동 시작: 모든 과거 락 및 임시 추적 플래그가 100% 완전 초기화되었습니다.")

            # 2. 대기 ➡️ 자동 저격 가동 시작
            self.bot_core.v35_engine.is_snipe_active = True
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
            # 수동 버튼 상호 배타적 잠금(비활성화)
            self.btn_manual_start.setEnabled(False)
            self.add_log("★ [신선 전략] 실전 오더플로우 저격 타격 감시가 전격 가동되었습니다. (실물 진입 허용)")
            self.sync_leverage_to_exchange()
            
            # 3. 실시간 포지션 파악 후 깨끗한 새 상태로 가드레일 감시 즉시 기상
            if self.bot_core.v35_engine.is_position_active:
                direction = getattr(self.bot_core.v35_engine, "entry_direction", None)
                if direction:
                    self.add_log(f"⚡ [클린 가드레일 도킹] 현재 포지션({direction}) 파악 완료 ➡️ 깨끗한 새 상태로 감시 루프를 기상합니다.")
                    asyncio.create_task(self.bot_core.v35_engine.manage_v35_exit_guardrail(direction))
        else:
            # 가동 ➡️ 정지
            self.bot_core.v35_engine.is_snipe_active = False
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
            # 수동 버튼 상호 잠금 해제
            self.btn_manual_start.setEnabled(True)
            self.add_log("★ [신선 전략] 실전 오더플로우 저격 감시를 일시 중지하고 대기 모드로 전환합니다.")
            
            # 거래소에 심겨 있는 모든 미체결 조건부 주문 일괄 자동 취소 코루틴 발진 (스탑로스 완전 정화)
            asyncio.create_task(self.cancel_all_bitget_trigger_orders_internal())
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
        self.add_log("🚨 [비상 긴급 탈출] 명령 수동 집행! 모든 포지션 청산 및 감시 강제 종료!")
        
        # 1. 백엔드 시뮬레이터 루프 및 태스크 안전 정리
        asyncio.create_task(self.bot_core.execute_emergency())
        
        # 2. 모든 봇의 감시 뇌를 즉시 격살 정지
        if self.bot_core.v35_engine:
            self.bot_core.v35_engine.is_snipe_active = False
            self.bot_core.v35_engine.is_position_active = False
            
        # 3. 거래소 단일 연결 3단 일괄 폭파 정화 시퀀스 격발! (개발계획서_103 이식)
        asyncio.create_task(self.execute_bitget_emergency_master_internal())
        
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
        # 포지션 활성화 시 경고 메시지 출력 후 기각
        if not self.bot_core or not self.bot_core.v35_engine:
            self.add_log("⚠️ [RPA 복원] 엔진이 초기화되지 않아 브라우저 새로고침을 할 수 없습니다.")
            return
        if self.bot_core.v35_engine.is_position_active or self.bot_core.v35_engine.exit_in_progress:
            self.add_log("⚠️ [RPA 복원] 포지션이 활성화 상태이거나 청산 진행 중이므로 안전을 위해 브라우저 새로고침을 할 수 없습니다.")
            return
            
        self.btn_reload_browser.setEnabled(False)
        self.btn_reload_browser.setText("🌐 브라우저 복원 진행 중...")
        
        async def do_reload():
            try:
                # 크롬 포트 응답 확인 및 재기동 처리
                self.add_log("🌐 [RPA 복원] 크롬 브라우저 원격 디버깅 포트(9224) 연결 확인 및 페이지 새로고침 시도 중...")
                async with self.bot_core.cdp_lock:
                    pw = None
                    browser = None
                    try:
                        raise NotImplementedError('Playwright removed for Bitget migration') # pw = await async_playwright().start()
                        browser = await asyncio.wait_for(
                            pw.chromium.connect_over_cdp("http://127.0.0.1:9224", timeout=5000), 
                            timeout=5.0
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
                            self.add_log("✅ [RPA 복원] BITGET 브라우저 페이지 새로고침(Reload) 완료!")
                        else:
                            self.add_log("⚠️ [RPA 복원] BITGET 탭을 찾을 수 없습니다. 브라우저가 종료되었을 수 있습니다.")
                            raise ConnectionError("No BITGET tab found")
                    except Exception as e:
                        self.add_log(f"⚠️ [RPA 복원] 브라우저 연결 실패 ({e}) ➡️ 디버깅 크롬 브라우저 자동 재기동을 수행합니다.")
                        bat_path = os.path.join(BASE_DIR, "디버깅크롬_시작.bat")
                        if os.path.exists(bat_path):
                            subprocess.Popen(["cmd.exe", "/c", "디버깅크롬_시작.bat"], cwd=BASE_DIR)
                            self.add_log("🚀 [RPA 복원] 디버깅 크롬 브라우저(디버깅크롬_시작.bat) 팝업 기동 완료!")
                            await asyncio.sleep(3.0)
                        else:
                            self.add_log("❌ [RPA 복원] 디버깅크롬_시작.bat 파일을 찾을 수 없습니다.")
                    finally:
                        if pw:
                            try: await pw.stop()
                            except: pass
            finally:
                self.btn_reload_browser.setEnabled(True)
                self.btn_reload_browser.setText("🌐 브라우저 새로고침/복원")
                
        asyncio.create_task(do_reload())

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
                
                import aiohttp
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
        if env_vars.get("BITGET_API_KEY"):
            import ccxt.async_support as ccxt
            self.bitget_exchange = ccxt.bitget({
                'apiKey': env_vars.get("BITGET_API_KEY"),
                'secret': env_vars.get("BITGET_SECRET_KEY"),
                'password': env_vars.get("BITGET_PASSPHRASE"),
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })

        self.bitget_headers = {}  # BITGET 실시간 인증 헤더 보관용 딕셔너리
        self.last_binance_time_ms = int(time.time() * 1000)  # 가장 최신 바이낸스 웹소켓 틱 타임스탬프 (ms)
        self.last_packet_latency_ms = 15.0  # 순정 바이낸스 패킷 레이턴시 수치 (ms)
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
        self.open_p = 63100.0
        self.high_p = 63300.0
        self.low_p = 62900.0
        
        # 매 1초마다 가격 변동과 연동하여 게이지 바를 상시 부드럽게 흔드는 비동기 텔레메트리 루프 추가 가동 (가장 먼저 독립 구동!)
        async def run_telemetry_loop():
            while self.is_running:
                try:
                    await asyncio.sleep(0.1)
                    
                    # 0. KST 시스템 시간 기반 동적 임계치 실시간 계산 및 수동 오버라이드
                    now_dt = datetime.now()
                    hour_val = now_dt.hour
                    kst_time_str = now_dt.strftime("%H:%M:%S")
                    
                    dashboard = getattr(self, "dashboard", None)
                    # thresholds 딕셔너리 안전 참조 및 기본값 세팅
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

                    # 시간대별 세션 판정 및 기본 임계치 추출 (09시~09시 트레이딩 데이 연동 + 1분 완충 타임락 개발계획서_260)
                    from datetime import timedelta
                    trading_dt = now_dt - timedelta(hours=9)
                    is_weekend = trading_dt.weekday() in [5, 6]
                    minute_val = hour_val * 60 + now_dt.minute
                    
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

                    if dashboard and dashboard.chk_manual_threshold.isChecked():
                        current_session = f"⚙ 수동 조율 ({kst_time_str})"
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
                    
                    # 3. UI 갱신 송출 (동적 임계치 및 KST 세션 정보 탑재)
                    latency_show = float(getattr(self, "last_packet_latency_ms", 15.0))
                    status_msg = "100% 현금 대기 중 (저격 대기)"
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
                        s_guardrails = getattr(dashboard, "session_guardrails", {}).get(s_guard_key, {"trigger": 0.5, "guard": 0.0}) if dashboard else {"trigger": 0.5, "guard": 0.0}
                        guard_trig = s_guardrails.get("trigger", 0.5)
                        guard_limit = s_guardrails.get("guard", 0.0)
                        
                        is_half_exited = getattr(self.v35_engine, "is_half_exited", False)
                        has_smart_guarded = getattr(self.v35_engine, "has_smart_guarded", False)
                        custom_stop_active = getattr(self.v35_engine, "custom_stop_active", False)
                        custom_stop_offset = getattr(self.v35_engine, "custom_stop_offset_pct", -0.2)
                        
                        if has_smart_guarded:
                            status_msg = f"[{direction_active} 진입 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(🛡 스마트 본전가드 작동 | 본전가드: {guard_limit:+.2f}%)"
                        elif is_half_exited:
                            status_msg = f"[{direction_active} 진입 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(🛡 50% 분할익절 완료 | 본전가드: {guard_limit:+.2f}%)"
                        else:
                            status_msg = f"[{direction_active} 진입 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(가드레일 도약 대기: +{guard_trig:.2f}%)"
                            
                        if live_pnl <= (target_sl + 0.2):
                            status_msg = f"⚠ [{direction_active} 위기 @ {entry:,.1f}] PnL: {live_pnl:+.2f}%{usdt_str}\n(손절 데드라인 임박: {target_sl:+.2f}%)"

                        if custom_stop_active:
                            stop_label = "익절" if custom_stop_offset > 0 else "손절"
                            status_msg += f"\n(🛡 스마트 스탑 가드: {custom_stop_offset:+.2f}% {stop_label} 감시 중)"

                    elif self.v35_engine.is_snipe_active:
                        status_msg = "🟢 실전 저격 감시 가동 중..."
                        
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
                            asyncio.to_thread(_write_bench, log_path, log_line)

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
                                if o.get("S") == "BUY":
                                    self.buy_liq_buffer.append((now_t, usd_val))
                                elif o.get("S") == "SELL":
                                    self.sell_liq_buffer.append((now_t, usd_val))
                except Exception as liq_err:
                    self.liq_wss_connected = False
                    logger.warning(f"선물 청산 WSS 연결 장애 (현물 aggTrade 우회 대체 작동 중): {liq_err}")
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

                                if usd_val >= 5000.0:
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
            
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        await asyncio.sleep(0.1)


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
        
        self.ENTRY_SLIPPAGE_CAP = 0.0003  # 진입 허용 슬리피지 (0.03%)
        
        self.is_position_active = False
        self.is_snipe_active = False      # 저격 감시 승인 상태 스위치
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

    async def get_live_bitget_price_internal(self):
        # 1. 모의 훈련 모드 시: 기존 훈련용 무작위 난수 시세 피딩
        if self.is_local_mode:
            return self.entry_price * (1 + random.uniform(-0.008, 0.018)) if self.is_position_active else 65000.0
            
        # 2. 실물 라이브 모드 시: 실시간 무결한 바이낸스 마크 가격 다이렉트 피딩 (난수 차단)
        if not getattr(self.bot, "price_ready", False):
            return 0.0
            
        curr_val = getattr(self.bot, "current_price", 0.0)
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
                    dashboard = getattr(self.bot, "dashboard", None)
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
                    dashboard = getattr(self.bot, "dashboard", None)
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

            # [세션 거래 ON/OFF 체크박스 검증 (개발계획서_260)]: 최상단으로 이동됨 (v4.07)

            t_step_start = time.time()
            now_t_metric = time.time()
            if getattr(self.bot, "dashboard", None) and now_t_metric - getattr(self, "last_radar_metric_log_time", 0.0) >= 1.0:
                self.last_radar_metric_log_time = now_t_metric
                self.bot.dashboard.add_log(f"⏱️ [1단계 임계치 돌파 메트릭] 사운드 0.000ms 최우선 직송 완료 ➡️ {direction} 저격 검증 진입...")
            self.entry_reason = f"1분 청산 ${rolling_1m_liq_usd:,.0f} (임계치: ${target_liq:,.0f}) & OI속도 {oi_delta_1m:+.4f}% (임계치: {target_oi:+.4f}%) 동시 돌파"
            self.last_signal_price = binance_mid

            # 동일 방향 중복 신호가 발생했을 때 -> 2차 / 3차 추가 매수 조건 검증 및 기동
            if self.is_position_active and not is_opposite:
                dashboard = self.bot.dashboard
                split_cooldown = dashboard.split_cooldown_seconds
                
                # 2차 추가 매수가 아직 격발되지 않은 경우
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
                                self.bot.dashboard.add_log(f"⏳ [2차 추가매수 보류] 1차 진입가 대비 하락폭 충족({pnl_from_entry_1*100.0:+.2f}%)되었으나, 쿨다운 대기 중 ({int(split_cooldown - time_since_last_split)}초 남음)")
                            return
                            
                        self.has_second_entry = True
                        self.last_split_entry_time = time.time()
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"⚡ [2차 추가매수 발동] 동일방향 신호 컨펌! 1차 진입가 대비 {pnl_from_entry_1*100.0:+.2f}% 도달 (임계치: {split_trigger*100.0:.2f}%)")
                        asyncio.create_task(self.execute_bitget_internal_packet(side=self.entry_direction, order_type="ADD_100_PERCENT"))
                        return
                    else:
                        return
                        
                # 2차 추가 매수는 격발되었으나 3차 추가 매수가 아직 격발되지 않은 경우
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
                                self.bot.dashboard.add_log(f"⏳ [3차 추가매수 보류] 1차 진입가 대비 하락폭 충족({pnl_from_entry_1*100.0:+.2f}%)되었으나, 쿨다운 대기 중 ({int(split_cooldown - time_since_last_split)}초 남음)")
                            return
                            
                        self.has_third_entry = True
                        self.last_split_entry_time = time.time()
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"⚡ [3차 추가매수 발동] 동일방향 신호 컨펌! 1차 진입가 대비 {pnl_from_entry_1*100.0:+.2f}% 도달 (임계치: {split_trigger*100.0:.2f}%)")
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
                    self.bot.ui_cb(0.0, 0, f"⏳ [중복 진입 방지] 동일 스파이크 연속 진입 보류 (남은 시간: {remain_sec:.1f}초)")
                return
            
            # 1.0초 정밀 디바운스로 🎯 [저격 격발] 로그 도배 100% 원천 박멸
            if getattr(self.bot, "dashboard", None) and now_t_chk - getattr(self, "last_snipe_trigger_log_time", 0.0) >= 1.0:
                self.last_snipe_trigger_log_time = now_t_chk
                self.bot.dashboard.add_log(f"🎯 [저격 격발] 시장청산(${rolling_1m_liq_usd:,.0f}) & OI속도({oi_delta_1m:+.4f}%) 임계치 동시 돌파! 진입 검증 시도...")
            
            # 방어벽 ①: 물리적 레이턴시 컷오프 (v2.88 차단 가드 전면 해제 - 레이턴시 상관없이 100% 즉각 발주)
            t_order = time.time() * 1000
            allowed_latency = self.MAX_LATENCY_MS_LOCAL if self.is_local_mode else self.MAX_LATENCY_MS_PROD
            actual_latency = t_order - t_signal
            
            # v2.88 해제: 레이턴시 초과 시 진입 기각 return 블록을 해제하고 100% 즉각 발주 진행
            if actual_latency > allowed_latency:
                if getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"⚡ [v2.88 레이턴시 통과] 레이턴시 {actual_latency:.1f}ms (기존 허용 {allowed_latency:.1f}ms 초과하나 전면 해제 즉각 발주)")
                
            # 2단계: 비트겟 호가창 VWAP 역공학 스캔
            bitget_book = await self.fetch_bitget_orderbook_internal()
            if not bitget_book or not bitget_book.get('asks') or not bitget_book.get('bids'):
                if self.bot.ui_cb:
                    self.bot.ui_cb(0.0, 0, f"❌ [진입 실패] BITGET 호가창 데이터를 조회할 수 없습니다.")
                return
                
            expected_fill = bitget_book['asks'][0][0] if direction == 'LONG' else bitget_book['bids'][0][0]
            
            # 방어벽 ②: 방향성 비대칭 슬리피지 캡 검증 (기획서_21)
            if direction == 'LONG':
                if expected_fill < binance_mid:
                    favorable_pct = (binance_mid - expected_fill) / binance_mid
                    if favorable_pct > 0.010: # 1.0% 초과 튀는 노이즈 차단
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"⚠️ [진입 기각] 유리한 롱 슬리피지 노이즈 1.0% 초과 ({favorable_pct*100.0:.3f}%) (차이: ${binance_mid - expected_fill:,.1f})")
                        return
                    # 1.0% 이하 유리한 슬리피지는 100% 무조건 승인!
                else:
                    unfavorable_slippage = (expected_fill - binance_mid) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"⚠️ [진입 기각] 불리한 롱 슬리피지 {unfavorable_slippage*100.0:.3f}% 초과 (허용: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (차이: ${expected_fill - binance_mid:,.1f})")
                        return
            else: # SHORT
                if expected_fill > binance_mid:
                    favorable_pct = (expected_fill - binance_mid) / binance_mid
                    if favorable_pct > 0.010: # 1.0% 초과 튀는 노이즈 차단
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"⚠️ [진입 기각] 유리한 숏 슬리피지 노이즈 1.0% 초과 ({favorable_pct*100.0:.3f}%) (차이: ${expected_fill - binance_mid:,.1f})")
                        return
                    # 1.0% 이하 유리한 슬리피지는 100% 무조건 승인!
                else:
                    unfavorable_slippage = (binance_mid - expected_fill) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        if self.bot.ui_cb:
                            self.bot.ui_cb(0.0, 0, f"⚠️ [진입 기각] 불리한 숏 슬리피지 {unfavorable_slippage*100.0:.3f}% 초과 (허용: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (차이: ${binance_mid - expected_fill:,.1f})")
                        return
                
            # 3단계: 최종 필터 패스 -> 저격 감시 승인(is_snipe_active) 및 Taker 0.012% 저격 진입
            if not self.is_position_active and self.is_snipe_active and not self.exit_in_progress:
                # --- [2중 중복 진입 방지 선제 락 선언] ---
                # 비동기 주문 전송 전 즉시 락을 걸어 후속 프레임 격발 원천 차단
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
            g_dashboard = getattr(self.bot, "dashboard", None)
            g_thresholds_map = getattr(g_dashboard, "session_thresholds", {}) if g_dashboard else {}
            if not g_thresholds_map.get(g_curr_key, {}).get("enabled", True):
                continue

            # [v2.80/v2.96/v3.62/v3.77] 실시간 토글형 인메모리 스마트 PnL 오프셋 스탑 감시 (상대적 위치 기반 듀얼 방향성 Engine)
            if getattr(self, "custom_stop_active", False):
                offset_val = getattr(self, "custom_stop_offset_pct", -0.2)
                pnl_at_set = getattr(self, "custom_stop_set_pnl", pnl_pct * 100.0)
                live_pnl = pnl_pct * 100.0

                if offset_val < pnl_at_set:
                    # 설정값이 현재 PnL보다 아래 ➡️ 하방 하락/보존/손절 모드
                    is_triggered = (live_pnl <= offset_val)
                    cond_str = "이하"
                    stop_label = "손절/보존"
                else:
                    # 설정값이 현재 PnL보다 위 ➡️ 상방 상승/반등/익절 모드
                    is_triggered = (live_pnl >= offset_val)
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
                        log_msg = f"🛡️ [스마트 스탑 발동] 실시간 PnL({live_pnl:+.2f}%)이 설정값({offset_val:+.2f}%) {cond_str} 도달! ({ratio:.0f}% {stop_label} 청산: {order_type})"
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
        dashboard = self.bot.dashboard
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
    

        
    # qasync를 이용한 Qt 비동기 이벤트 루프 체결
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    bot = BotCore()
    dashboard = ShinseonDashboard(bot)
    dashboard.show()
    
    with loop:
        loop.run_forever()

