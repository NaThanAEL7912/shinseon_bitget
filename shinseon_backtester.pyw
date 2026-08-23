# -*- coding: utf-8 -*-
"""
신선(SHINSEON) 오더플로우 전문 독립 전략 백테스터 GUI (ShinSeon Strategy Backtester V1.0)
- 3대 설정 탭(세션별 설정, 트레이딩 핵심 설정, 가드레일 설정) 100% 연동
- 시작일시~종료일시 기간 필터링 및 원클릭 프리셋
- 실시간 성과 대시보드, 세션별 성과표, 초단위 매매일지, CSV 내보내기, 황금 파라미터 자동 최적화 탑재
"""

import os
import sys
import json
import csv
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QDateTimeEdit, QComboBox, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal
from PySide6.QtGui import QFont, QColor, QIcon

from backtest_engine import run_backtest_simulation, load_all_session_data

CONFIG_FILE = "shinseon_config.json"

# ================= 최고급 네온 다크 & 골드 스타일시트 =================
DARK_GOLD_STYLE = """
QMainWindow, QWidget {
    background-color: #0c0d10;
    color: #e6e6e6;
    font-family: 'Malgun Gothic', 'Noto Sans KR', 'Segoe UI', sans-serif;
    font-size: 12px;
}

QTabWidget::pane {
    border: 1px solid #2a2d36;
    background-color: #12141a;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #171a21;
    color: #9da3b4;
    padding: 10px 24px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    border: 1px solid #20232b;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #1f232d;
    color: #ffd700;
    border: 1px solid #ffd700;
    border-bottom: 2px solid #1f232d;
}

QTabBar::tab:hover {
    color: #ffffff;
    background-color: #1c202a;
}

QGroupBox {
    border: 1px solid #242833;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    background-color: #13151c;
    font-weight: bold;
    color: #ffd700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}

QLineEdit, QDateTimeEdit, QComboBox {
    background-color: #090a0d;
    border: 1px solid #2e3342;
    border-radius: 5px;
    padding: 6px 10px;
    color: #ffffff;
    font-weight: bold;
}

QLineEdit:focus, QDateTimeEdit:focus, QComboBox:focus {
    border: 1px solid #ffd700;
    background-color: #0f1117;
}

QPushButton {
    background-color: #1c202a;
    color: #e6e6e6;
    border: 1px solid #313747;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #262c3b;
    border: 1px solid #ffd700;
    color: #ffd700;
}

QPushButton#btn_run {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d4af37, stop:1 #ffd700);
    color: #000000;
    font-size: 14px;
    font-weight: 900;
    border: none;
    padding: 10px 24px;
    border-radius: 6px;
}

QPushButton#btn_run:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6c35c, stop:1 #fff066);
    box-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
}

QPushButton#btn_preset {
    background-color: #141720;
    border: 1px solid #2b3140;
    color: #a0a8b9;
    padding: 5px 12px;
    font-size: 11px;
}

QPushButton#btn_preset:hover {
    color: #00ffcc;
    border-color: #00ffcc;
}

QTableWidget {
    background-color: #0e1015;
    border: 1px solid #232732;
    gridline-color: #1d212b;
    border-radius: 6px;
    color: #f0f0f0;
}

QHeaderView::section {
    background-color: #161922;
    color: #ffd700;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #2e3342;
    font-weight: bold;
}

QTableWidget::item:selected {
    background-color: #2b3242;
    color: #ffd700;
}

QScrollBar:vertical {
    border: none;
    background: #0d0f14;
    width: 8px;
}

QScrollBar::thumb:vertical {
    background: #2b3140;
    border-radius: 4px;
}

QScrollBar::thumb:vertical:hover {
    background: #ffd700;
}

QCheckBox {
    color: #e0e0e0;
    font-weight: bold;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #3a4154;
    background-color: #0e1015;
}

QCheckBox::indicator:checked {
    background-color: #ffd700;
    border: 1px solid #ffd700;
    image: none;
}
"""

class ShinseonBacktesterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("신선(神選) 오더플로우 전문 독립 전략 백테스터 V1.0 [SHINSEON BACKTESTER]")
        self.resize(1400, 920)
        self.setStyleSheet(DARK_GOLD_STYLE)

        self.last_results = None
        self.init_ui()
        self.load_config_defaults()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. 상단 타이틀 & 📅 기간 필터링 컨트롤러
        header_widget = self.create_header_and_date_picker()
        main_layout.addWidget(header_widget)

        # 2. 메인 스플리터 (상단 설정 탭 vs 하단 결과 대시보드)
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(6)

        # 상단 설정 영역 (탭 컨트롤러)
        self.tab_widget = QTabWidget()
        self.tab_sessions = self.create_sessions_tab()
        self.tab_trading = self.create_trading_tab()
        self.tab_guardrails = self.create_guardrails_tab()
        self.tab_funds = self.create_funds_tab()

        self.tab_widget.addTab(self.tab_sessions, "1. 세션별 설정 (청산/OI/손절)")
        self.tab_widget.addTab(self.tab_trading, "2. 트레이딩 핵심 설정 (배팅비중/DCA/쿨타임)")
        self.tab_widget.addTab(self.tab_guardrails, "3. 가드레일 설정 (2단계익절/본전가드)")
        self.tab_widget.addTab(self.tab_funds, "4. 자금 & 수수료 설정 (박호두50%)")
        
        splitter.addWidget(self.tab_widget)

        # 하단 결과 대시보드 영역
        results_widget = self.create_results_dashboard()
        splitter.addWidget(results_widget)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter)

    # -------------------------------------------------------------
    # 1. 헤더 및 📅 기간 필터링 제어판
    # -------------------------------------------------------------
    def create_header_and_date_picker(self):
        group = QGroupBox("📅 백테스팅 기간 필터링 & 빠른 선택 제어판 (Date & Time Picker)")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top_h = QHBoxLayout()
        title_lbl = QLabel("<b style='font-size: 16px; color: #ffd700;'>神選 [SHINSEON] 전략 백테스터</b> <span style='color: #8b949e;'>v1.0 (9일간 초단위 실측 오더플로우 전수 탑재)</span>")
        top_h.addWidget(title_lbl)
        top_h.addStretch()

        # 액션 버튼들
        self.btn_run = QPushButton("🚀 백테스트 실행 (Run Backtest)")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.clicked.connect(self.on_run_backtest)
        top_h.addWidget(self.btn_run)

        self.btn_save_cfg = QPushButton("💾 설정 저장")
        self.btn_save_cfg.clicked.connect(self.on_save_config)
        top_h.addWidget(self.btn_save_cfg)

        self.btn_load_cfg = QPushButton("📂 설정 불러오기")
        self.btn_load_cfg.clicked.connect(self.on_load_config_file)
        top_h.addWidget(self.btn_load_cfg)

        self.btn_reset = QPushButton("🔄 기본값 복원")
        self.btn_reset.clicked.connect(self.load_config_defaults)
        top_h.addWidget(self.btn_reset)

        layout.addLayout(top_h)

        # 기간 선택 바
        date_h = QHBoxLayout()
        date_h.setSpacing(10)

        date_h.addWidget(QLabel("<b style='color: #00ffcc;'>시작 일시:</b>"))
        self.dt_start = QDateTimeEdit(QDateTime.fromString("2026-08-10 09:00:00", "yyyy-MM-dd HH:mm:ss"))
        self.dt_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_start.setCalendarPopup(True)
        date_h.addWidget(self.dt_start)

        date_h.addWidget(QLabel("<b style='color: #ff3366;'>종료 일시:</b>"))
        self.dt_end = QDateTimeEdit(QDateTime.fromString("2026-08-18 16:30:00", "yyyy-MM-dd HH:mm:ss"))
        self.dt_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_end.setCalendarPopup(True)
        date_h.addWidget(self.dt_end)

        # 빠른 프리셋 버튼들
        btn_full = QPushButton("전체 기간 (Full)")
        btn_full.setObjectName("btn_preset")
        btn_full.clicked.connect(lambda: self.set_date_preset("full"))
        date_h.addWidget(btn_full)

        btn_24h = QPushButton("최근 24시간")
        btn_24h.setObjectName("btn_preset")
        btn_24h.clicked.connect(lambda: self.set_date_preset("24h"))
        date_h.addWidget(btn_24h)

        btn_3d = QPushButton("최근 3일")
        btn_3d.setObjectName("btn_preset")
        btn_3d.clicked.connect(lambda: self.set_date_preset("3d"))
        date_h.addWidget(btn_3d)

        btn_weekday = QPushButton("지난주 평일 (월~금)")
        btn_weekday.setObjectName("btn_preset")
        btn_weekday.clicked.connect(lambda: self.set_date_preset("weekday"))
        date_h.addWidget(btn_weekday)

        btn_weekend = QPushButton("지난주 주말 (토~일)")
        btn_weekend.setObjectName("btn_preset")
        btn_weekend.clicked.connect(lambda: self.set_date_preset("weekend"))
        date_h.addWidget(btn_weekend)

        date_h.addStretch()
        layout.addLayout(date_h)

        return group

    def set_date_preset(self, preset):
        if preset == "full":
            self.dt_start.setDateTime(QDateTime.fromString("2026-08-10 09:00:00", "yyyy-MM-dd HH:mm:ss"))
            self.dt_end.setDateTime(QDateTime.fromString("2026-08-18 16:30:00", "yyyy-MM-dd HH:mm:ss"))
        elif preset == "24h":
            self.dt_start.setDateTime(QDateTime.fromString("2026-08-17 16:30:00", "yyyy-MM-dd HH:mm:ss"))
            self.dt_end.setDateTime(QDateTime.fromString("2026-08-18 16:30:00", "yyyy-MM-dd HH:mm:ss"))
        elif preset == "3d":
            self.dt_start.setDateTime(QDateTime.fromString("2026-08-15 00:00:00", "yyyy-MM-dd HH:mm:ss"))
            self.dt_end.setDateTime(QDateTime.fromString("2026-08-18 16:30:00", "yyyy-MM-dd HH:mm:ss"))
        elif preset == "weekday":
            self.dt_start.setDateTime(QDateTime.fromString("2026-08-10 09:00:00", "yyyy-MM-dd HH:mm:ss"))
            self.dt_end.setDateTime(QDateTime.fromString("2026-08-15 05:00:00", "yyyy-MM-dd HH:mm:ss"))
        elif preset == "weekend":
            self.dt_start.setDateTime(QDateTime.fromString("2026-08-15 05:00:00", "yyyy-MM-dd HH:mm:ss"))
            self.dt_end.setDateTime(QDateTime.fromString("2026-08-17 09:00:00", "yyyy-MM-dd HH:mm:ss"))

    # -------------------------------------------------------------
    # 2. [탭 1: 세션별 설정] (스크린샷 1과 100% 동일)
    # -------------------------------------------------------------
    def create_sessions_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        s_layout = QVBoxLayout(scroll_content)

        # 세션 정의
        self.session_inputs = {}
        sessions_def = [
            ("평일 4대 세션", [
                ("asia", "아시아 (09:00 ~ 16:30)", 250000, 0.0400, -0.6, True),
                ("europe", "유럽 (16:30 ~ 22:30)", 600000, 0.0600, -0.8, True),
                ("us", "미국 본장 (22:30 ~ 05:00)", 650000, 0.1800, -1.3, True),
                ("pacific", "태평양 횡보 (05:00 ~ 09:00)", 50000, 0.0100, -0.8, False),
            ]),
            ("주말 4대 세션", [
                ("weekend_asia", "주말 아시아 (09:00 ~ 16:30)", 20000, 0.0400, -0.6, True),
                ("weekend_europe", "주말 유럽 (16:30 ~ 22:30)", 30000, 0.0500, -0.6, True),
                ("weekend_us", "주말 미국 본장 (22:30 ~ 05:00)", 50000, 0.0400, -0.8, True),
                ("weekend_pacific", "주말 태평양 (05:00 ~ 09:00)", 15000, 0.0300, -0.5, False),
            ])
        ]

        for group_title, s_list in sessions_def:
            grp = QGroupBox(group_title)
            g_layout = QVBoxLayout(grp)

            # 헤더 행
            h_row = QHBoxLayout()
            h_row.addWidget(QLabel("<b>세션 구분</b>"), 2)
            h_row.addWidget(QLabel("<b>1분 청산액 ($)</b>"), 2)
            h_row.addWidget(QLabel("<b>1분 이속도/OI속도 (%)</b>"), 2)
            h_row.addWidget(QLabel("<b>최초 손절선 (%)</b>"), 2)
            g_layout.addLayout(h_row)

            for key, name, liq_val, oi_val, sl_val, enabled_val in s_list:
                row = QHBoxLayout()
                chk = QCheckBox(name)
                chk.setChecked(enabled_val)
                row.addWidget(chk, 2)

                ed_liq = QLineEdit(f"{liq_val:,}")
                ed_liq.setAlignment(Qt.AlignCenter)
                row.addWidget(ed_liq, 2)

                ed_oi = QLineEdit(f"{oi_val:.4f}")
                ed_oi.setAlignment(Qt.AlignCenter)
                row.addWidget(ed_oi, 2)

                ed_sl = QLineEdit(f"{sl_val:.1f}")
                ed_sl.setAlignment(Qt.AlignCenter)
                row.addWidget(ed_sl, 2)

                self.session_inputs[key] = {
                    'enabled': chk,
                    'liq': ed_liq,
                    'oi': ed_oi,
                    'sl': ed_sl
                }
                g_layout.addLayout(row)

            s_layout.addWidget(grp)

        s_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return widget

    # -------------------------------------------------------------
    # 3. [탭 2: 트레이딩 핵심 설정] (스크린샷 2와 100% 동일 다중 컬럼)
    # -------------------------------------------------------------
    def create_trading_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        t_layout = QVBoxLayout(scroll_content)

        self.trading_inputs = {}
        sessions_keys = [
            ("asia", "아시아 (09~16:30)"),
            ("europe", "유럽/런던 (16:30~22:30)"),
            ("us", "미국 본장 (22:30~05:00)"),
            ("pacific", "태평양 (05:00~09:00)"),
            ("weekend_asia", "주말 아시아"),
            ("weekend_europe", "주말 유럽"),
            ("weekend_us", "주말 미국"),
            ("weekend_pacific", "주말 태평양")
        ]

        param_rows = [
            ("⚡ 포지션 레버리지 (1~150배)", "leverage", [30, 30, 30, 30, 30, 30, 30, 30]),
            ("💰 1차 매수 비중 (%)", "buy1_ratio", [300.0, 300.0, 600.0, 200.0, 300.0, 300.0, 300.0, 200.0]),
            ("💰 2차 매수 비중 (%)", "buy2_ratio", [150.0, 150.0, 300.0, 100.0, 150.0, 150.0, 150.0, 100.0]),
            ("📉 2차 진입 하락폭 (1차 대비 %)", "dca_drop", [-0.30, -0.30, -0.30, -0.30, -0.30, -0.30, -0.30, -0.30]),
            ("⏳ 추가 매수 후 진입제한 (초)", "dca_time_limit", [900.0, 900.0, 900.0, 900.0, 900.0, 900.0, 900.0, 900.0]),
            ("🔵 손절 후 진입제한 (초)", "sl_cooldown", [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0]),
            ("🟣 익절 후 진입제한 (초)", "tp_cooldown", [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
        ]

        grp = QGroupBox("세션별 독립 트레이딩 핵심 파라미터 그리드")
        g_layout = QVBoxLayout(grp)

        # 테이블 헤더 행
        header_h = QHBoxLayout()
        header_h.addWidget(QLabel("<b style='color:#ffd700;'>파라미터 항목</b>"), 3)
        for _, s_title in sessions_keys[:4]: # 평일 4대
            lbl = QLabel(f"<b>{s_title}</b>")
            lbl.setAlignment(Qt.AlignCenter)
            header_h.addWidget(lbl, 2)
        g_layout.addLayout(header_h)

        for p_label, p_key, p_defaults in param_rows:
            row_h = QHBoxLayout()
            row_h.addWidget(QLabel(p_label), 3)

            for idx, (s_k, _) in enumerate(sessions_keys[:4]):
                if s_k not in self.trading_inputs:
                    self.trading_inputs[s_k] = {}
                ed = QLineEdit(str(p_defaults[idx]))
                ed.setAlignment(Qt.AlignCenter)
                self.trading_inputs[s_k][p_key] = ed
                row_h.addWidget(ed, 2)

            g_layout.addLayout(row_h)

        t_layout.addWidget(grp)

        # 주말 4대 세션 그리드
        grp_w = QGroupBox("주말 4대 세션 트레이딩 파라미터 그리드")
        gw_layout = QVBoxLayout(grp_w)

        header_w = QHBoxLayout()
        header_w.addWidget(QLabel("<b style='color:#ffd700;'>파라미터 항목</b>"), 3)
        for _, s_title in sessions_keys[4:]:
            lbl = QLabel(f"<b>{s_title}</b>")
            lbl.setAlignment(Qt.AlignCenter)
            header_w.addWidget(lbl, 2)
        gw_layout.addLayout(header_w)

        for p_label, p_key, p_defaults in param_rows:
            row_w = QHBoxLayout()
            row_w.addWidget(QLabel(p_label), 3)

            for idx, (s_k, _) in enumerate(sessions_keys[4:], start=4):
                if s_k not in self.trading_inputs:
                    self.trading_inputs[s_k] = {}
                ed = QLineEdit(str(p_defaults[idx]))
                ed.setAlignment(Qt.AlignCenter)
                self.trading_inputs[s_k][p_key] = ed
                row_w.addWidget(ed, 2)

            gw_layout.addLayout(row_w)

        t_layout.addWidget(grp_w)
        t_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return widget

    # -------------------------------------------------------------
    # 4. [탭 3: 가드레일 설정] (스크린샷 3과 100% 동일)
    # -------------------------------------------------------------
    def create_guardrails_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        g_layout = QVBoxLayout(scroll_content)

        self.guard_inputs = {}
        guard_sessions = [
            ("평일 4대 세션 가드레일", [
                ("asia", "아시아", 0.80, 1.20, 0.50),
                ("europe", "유럽(런던)", 1.00, 1.20, 0.50),
                ("us", "미국 본장", 1.50, 1.70, 1.00),
                ("pacific", "태평양", 0.50, 0.60, 0.20)
            ]),
            ("주말 4대 세션 가드레일", [
                ("weekend_asia", "주말 아시아", 0.50, 0.80, 0.10),
                ("weekend_europe", "주말 유럽(런던)", 0.40, 0.60, 0.10),
                ("weekend_us", "주말 미국 본장", 0.80, 1.20, 0.10),
                ("weekend_pacific", "주말 태평양", 0.40, 0.50, 0.10)
            ])
        ]

        for group_title, s_list in guard_sessions:
            grp = QGroupBox(group_title)
            layout_grp = QVBoxLayout(grp)

            # 헤더
            h_row = QHBoxLayout()
            h_row.addWidget(QLabel("<b>세션</b>"), 2)
            h_row.addWidget(QLabel("<b>1차 익절 PnL (%)</b>"), 2)
            h_row.addWidget(QLabel("<b>2차 익절 PnL (%)</b>"), 2)
            h_row.addWidget(QLabel("<b>본전/버퍼 가드 (PnL %)</b>"), 2)
            layout_grp.addLayout(h_row)

            for key, name, tp1, tp2, be in s_list:
                row = QHBoxLayout()
                row.addWidget(QLabel(name), 2)

                ed_tp1 = QLineEdit(f"{tp1:.2f}")
                ed_tp1.setAlignment(Qt.AlignCenter)
                row.addWidget(ed_tp1, 2)

                ed_tp2 = QLineEdit(f"{tp2:.2f}")
                ed_tp2.setAlignment(Qt.AlignCenter)
                row.addWidget(ed_tp2, 2)

                ed_be = QLineEdit(f"{be:.2f}")
                ed_be.setAlignment(Qt.AlignCenter)
                row.addWidget(ed_be, 2)

                self.guard_inputs[key] = {
                    'tp1': ed_tp1,
                    'tp2': ed_tp2,
                    'be_guard': ed_be
                }
                layout_grp.addLayout(row)

            g_layout.addWidget(grp)

        # 공통 가드레일 비율
        c_grp = QGroupBox("공통 분할 익절 및 추세 추종 설정")
        c_layout = QHBoxLayout(c_grp)

        c_layout.addWidget(QLabel("1차 분할 익절 비율 (%):"))
        self.ed_tp1_split = QLineEdit("50.0")
        self.ed_tp1_split.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(self.ed_tp1_split)

        c_layout.addWidget(QLabel("2차 분할 익절 비율 (%):"))
        self.ed_tp2_split = QLineEdit("50.0")
        self.ed_tp2_split.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(self.ed_tp2_split)

        g_layout.addWidget(c_grp)
        g_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return widget

    # -------------------------------------------------------------
    # 5. [탭 4: 자금 & 수수료 설정] (박호두 50% 할인 수수료)
    # -------------------------------------------------------------
    def create_funds_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        grp = QGroupBox("💰 계좌 자산 & 거래소 수수료율 설정 (Fee Rate)")
        g_layout = QVBoxLayout(grp)
        g_layout.setSpacing(12)

        # 시작 자산
        row_b = QHBoxLayout()
        row_b.addWidget(QLabel("<b>시작 계좌 시드 머니 (USDT):</b>"), 2)
        self.ed_initial_balance = QLineEdit("7020.14")
        self.ed_initial_balance.setAlignment(Qt.AlignCenter)
        row_b.addWidget(self.ed_initial_balance, 3)
        row_b.addStretch(2)
        g_layout.addLayout(row_b)

        # 수수료율 프리셋
        row_f = QHBoxLayout()
        row_f.addWidget(QLabel("<b>적용 수수료 체계 (Taker):</b>"), 2)
        self.cb_fee_preset = QComboBox()
        self.cb_fee_preset.addItem("👑 박호두 레퍼럴 50% 할인 (0.030% / 0.00030)", 0.00030)
        self.cb_fee_preset.addItem("비트겟 기본 표준 시장가 (0.060% / 0.00060)", 0.00060)
        self.cb_fee_preset.addItem("VIP / 페이백 결합 최상위 (0.025% / 0.00025)", 0.00025)
        self.cb_fee_preset.addItem("수수료 0% (수수료 미차감 원장 분석)", 0.00000)
        self.cb_fee_preset.currentIndexChanged.connect(self.on_fee_preset_changed)
        row_f.addWidget(self.cb_fee_preset, 3)

        self.ed_custom_fee = QLineEdit("0.00030")
        self.ed_custom_fee.setAlignment(Qt.AlignCenter)
        row_f.addWidget(self.ed_custom_fee, 1)
        row_f.addStretch(1)
        g_layout.addLayout(row_f)

        layout.addWidget(grp)
        layout.addStretch()
        return widget

    def on_fee_preset_changed(self, idx):
        val = self.cb_fee_preset.currentData()
        self.ed_custom_fee.setText(f"{val:.5f}")

    # -------------------------------------------------------------
    # 6. 하단 결과 대시보드 (종합 요약 + 세션별 성과 + 거래 일지)
    # -------------------------------------------------------------
    def create_results_dashboard(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # 8대 요약 카드 박스
        cards_grp = QGroupBox("📊 백테스팅 종합 성과 대시보드 (Performance Summary)")
        cards_layout = QHBoxLayout(cards_grp)
        cards_layout.setContentsMargins(10, 8, 10, 8)
        cards_layout.setSpacing(8)

        self.lbl_trades = self.create_metric_card("총 거래수", "0회 (0승 0패)", "#ffffff")
        self.lbl_winrate = self.create_metric_card("승률 (Win Rate)", "0.0%", "#00ffcc")
        self.lbl_gross = self.create_metric_card("수수료전 총수익", "+$0.00", "#e6e6e6")
        self.lbl_fee = self.create_metric_card("지불 수수료", "-$0.00", "#ff3366")
        self.lbl_net = self.create_metric_card("👑 최종 실질 순수익", "+$0.00", "#ffd700")
        self.lbl_krw = self.create_metric_card("원화 환산 순수익", "약 0 원", "#ffd700")
        self.lbl_roi = self.create_metric_card("수익률 (ROI)", "+0.00%", "#00ffcc")
        self.lbl_mdd = self.create_metric_card("최대 낙폭 (MDD)", "0.00%", "#ff3366")

        for card in [self.lbl_trades, self.lbl_winrate, self.lbl_gross, self.lbl_fee,
                     self.lbl_net, self.lbl_krw, self.lbl_roi, self.lbl_mdd]:
            cards_layout.addWidget(card)

        layout.addWidget(cards_grp)

        # 결과 서브 탭 (세션별 성과 vs 거래 상세 일지)
        self.res_tab_widget = QTabWidget()

        # 서브탭 1: 세션별 성과 테이블
        self.table_sessions = QTableWidget()
        self.table_sessions.setColumnCount(8)
        self.table_sessions.setHorizontalHeaderLabels([
            "세션 구분", "총 거래수", "승 / 패", "승률 (%)", "총수익 (Gross)", "지불 수수료", "👑 실질 순수익 (Net)", "수익률 (ROI)"
        ])
        self.table_sessions.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.res_tab_widget.addTab(self.table_sessions, "🌍 8대 세션별 성과 비교표")

        # 서브탭 2: 거래 상세 일지 테이블 & CSV 버튼
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(4, 4, 4, 4)

        log_btn_h = QHBoxLayout()
        self.lbl_log_count = QLabel("<b>총 0건의 매매 일지가 기록되었습니다.</b>")
        log_btn_h.addWidget(self.lbl_log_count)
        log_btn_h.addStretch()

        self.btn_export_csv = QPushButton("📥 매매 일지 엑셀/CSV 내보내기")
        self.btn_export_csv.clicked.connect(self.on_export_csv)
        log_btn_h.addWidget(self.btn_export_csv)
        log_layout.addLayout(log_btn_h)

        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(12)
        self.table_logs.setHorizontalHeaderLabels([
            "No.", "세션", "진입일시", "청산일시", "포지션", "4대 전략 구분", "진입가", "청산가", "최고 PnL", "청산 사유", "👑 순손익 ($)", "지불 수수료 ($)"
        ])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(9, QHeaderView.Stretch)
        log_layout.addWidget(self.table_logs)

        self.res_tab_widget.addTab(log_widget, "📜 초단위 거래 상세 일지 (Trade Logs)")
        layout.addWidget(self.res_tab_widget)

        return widget

    def create_metric_card(self, title, value, val_color):
        frame = QFrame()
        frame.setStyleSheet("background-color: #0e1015; border: 1px solid #232732; border-radius: 6px;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #8b949e; font-size: 11px;")
        lbl_t.setAlignment(Qt.AlignCenter)
        v.addWidget(lbl_t)

        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"color: {val_color}; font-size: 13px; font-weight: bold;")
        lbl_v.setAlignment(Qt.AlignCenter)
        v.addWidget(lbl_v)

        frame.lbl_val = lbl_v
        return frame

    # -------------------------------------------------------------
    # 7. 백테스트 실행 및 결과 렌더링
    # -------------------------------------------------------------
    def get_current_config_dict(self):
        # 1. 세션별 설정
        sessions_dict = {}
        for k, v in self.session_inputs.items():
            sessions_dict[k] = {
                'enabled': v['enabled'].isChecked(),
                'liq': float(v['liq'].text().replace(",", "").strip()),
                'oi': float(v['oi'].text().strip()),
                'sl': float(v['sl'].text().strip())
            }

        # 2. 트레이딩 핵심 설정
        trading_dict = {}
        for s_k, p_dict in self.trading_inputs.items():
            trading_dict[s_k] = {}
            for p_k, ed in p_dict.items():
                trading_dict[s_k][p_k] = float(ed.text().strip())

        # 3. 가드레일 설정
        guard_dict = {
            'tp1_split_ratio': float(self.ed_tp1_split.text().strip()),
            'tp2_split_ratio': float(self.ed_tp2_split.text().strip())
        }
        for s_k, g_dict in self.guard_inputs.items():
            guard_dict[s_k] = {
                'tp1': float(g_dict['tp1'].text().strip()),
                'tp2': float(g_dict['tp2'].text().strip()),
                'be_guard': float(g_dict['be_guard'].text().strip())
            }

        return {
            'initial_balance': float(self.ed_initial_balance.text().strip()),
            'fee_rate': float(self.ed_custom_fee.text().strip()),
            'sessions': sessions_dict,
            'trading': trading_dict,
            'guardrails': guard_dict
        }

    def on_run_backtest(self):
        try:
            cfg = self.get_current_config_dict()
            start_dt = self.dt_start.dateTime().toPython()
            end_dt = self.dt_end.dateTime().toPython()

            res = run_backtest_simulation(cfg, start_dt, end_dt)
            if 'error' in res:
                QMessageBox.critical(self, "오류", res['error'])
                return

            self.last_results = res
            self.render_results(res)
        except Exception as e:
            QMessageBox.critical(self, "백테스트 예외", f"시뮬레이션 실행 중 오류 발생: {e}")

    def render_results(self, res):
        init_b = res['initial_balance']
        net_b = res['total_net']
        roi = res['roi']
        krw = net_b * 1380

        # 카드 갱신
        self.lbl_trades.lbl_val.setText(f"{res['total_trades']}회 ({res['total_wins']}승 {res['total_losses']}패)")
        self.lbl_winrate.lbl_val.setText(f"{res['win_rate']:.1f}%")
        self.lbl_gross.lbl_val.setText(f"+${res['total_gross']:,.2f}")
        self.lbl_fee.lbl_val.setText(f"-${res['total_fee']:,.2f}")
        self.lbl_net.lbl_val.setText(f"+${net_b:,.2f}" if net_b >= 0 else f"-${abs(net_b):,.2f}")
        self.lbl_krw.lbl_val.setText(f"약 {krw:,.0f} 원")
        self.lbl_roi.lbl_val.setText(f"{roi:+.2f}%")
        self.lbl_mdd.lbl_val.setText(f"{res['mdd_pct']:.2f}% (${res['mdd_usdt']:,.2f})")

        # 세션별 성과 테이블 갱신
        summary = res['session_summary']
        self.table_sessions.setRowCount(len(summary))
        for row, (s_key, s_data) in enumerate(summary.items()):
            self.table_sessions.setItem(row, 0, QTableWidgetItem(s_data['name']))
            self.table_sessions.setItem(row, 1, QTableWidgetItem(f"{s_data['trades']}회"))
            self.table_sessions.setItem(row, 2, QTableWidgetItem(f"{s_data['wins']}승 {s_data['losses']}패"))
            self.table_sessions.setItem(row, 3, QTableWidgetItem(f"{s_data['win_rate']:.1f}%"))
            self.table_sessions.setItem(row, 4, QTableWidgetItem(f"+${s_data['gross']:,.2f}"))
            self.table_sessions.setItem(row, 5, QTableWidgetItem(f"-${s_data['fee']:,.2f}"))
            
            item_net = QTableWidgetItem(f"+${s_data['net']:,.2f}" if s_data['net'] >= 0 else f"-${abs(s_data['net']):,.2f}")
            item_net.setForeground(QColor("#00ffcc" if s_data['net'] >= 0 else "#ff3366"))
            self.table_sessions.setItem(row, 6, item_net)

            item_roi = QTableWidgetItem(f"{s_data['roi']:+.2f}%")
            item_roi.setForeground(QColor("#00ffcc" if s_data['roi'] >= 0 else "#ff3366"))
            self.table_sessions.setItem(row, 7, item_roi)

        # 거래 상세 일지 테이블 갱신
        logs = res['trade_logs']
        self.lbl_log_count.setText(f"<b>총 {len(logs)}건의 매매 일지가 기록되었습니다. (선택 기간 정밀 시뮬레이션 완료)</b>")
        self.table_logs.setRowCount(len(logs))

        for row, t in enumerate(logs):
            self.table_logs.setItem(row, 0, QTableWidgetItem(f"{row+1:03d}"))
            self.table_logs.setItem(row, 1, QTableWidgetItem(t.get('session', '')))
            self.table_logs.setItem(row, 2, QTableWidgetItem(t.get('entry_time', '')))
            self.table_logs.setItem(row, 3, QTableWidgetItem(t.get('exit_time', '')))
            
            item_dir = QTableWidgetItem(t.get('dir', ''))
            item_dir.setForeground(QColor("#00ffcc" if t.get('dir') == 'LONG' else "#ff3366"))
            self.table_logs.setItem(row, 4, item_dir)

            item_strat = QTableWidgetItem(t.get('strategy', '-'))
            item_strat.setForeground(QColor("#ffd700"))
            self.table_logs.setItem(row, 5, item_strat)

            self.table_logs.setItem(row, 6, QTableWidgetItem(f"${t.get('entry_price', 0.0):,.1f}"))
            self.table_logs.setItem(row, 7, QTableWidgetItem(f"${t.get('exit_price', 0.0):,.1f}"))
            self.table_logs.setItem(row, 8, QTableWidgetItem(f"+{t.get('peak_pnl_pct', 0.0):.2f}%"))
            self.table_logs.setItem(row, 9, QTableWidgetItem(t.get('reason', '')))

            net_v = t.get('net', 0.0)
            item_net = QTableWidgetItem(f"+${net_v:,.2f}" if net_v >= 0 else f"-${abs(net_v):,.2f}")
            item_net.setForeground(QColor("#00ffcc" if net_v >= 0 else "#ff3366"))
            self.table_logs.setItem(row, 10, item_net)

            self.table_logs.setItem(row, 11, QTableWidgetItem(f"-${t.get('fee', 0.0):,.2f}"))

    def on_export_csv(self):
        if not self.last_results or not self.last_results.get('trade_logs'):
            QMessageBox.warning(self, "알림", "내보낼 백테스트 결과 매매 일지가 없습니다. 먼저 백테스트를 실행해 주세요.")
            return

        fpath, _ = QFileDialog.getSaveFileName(self, "매매 일지 CSV 저장", "shinseon_backtest_logs.csv", "CSV Files (*.csv)")
        if not fpath:
            return

        try:
            logs = self.last_results['trade_logs']
            with open(fpath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["No", "세션", "진입일시", "청산일시", "방향", "4대 전략 구분", "진입가", "청산가", "최고PnL(%)", "청산사유", "순손익(USDT)", "수수료(USDT)"])
                for idx, t in enumerate(logs, 1):
                    writer.writerow([
                        idx, t.get('session'), t.get('entry_time'), t.get('exit_time'),
                        t.get('dir'), t.get('strategy', '-'), t.get('entry_price'), t.get('exit_price'),
                        f"{t.get('peak_pnl_pct', 0.0):.2f}%", t.get('reason'),
                        f"{t.get('net', 0.0):.2f}", f"{t.get('fee', 0.0):.2f}"
                    ])
            QMessageBox.information(self, "완료", f"매매 일지가 성공적으로 저장되었습니다:\n{fpath}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"CSV 저장 실패: {e}")

    def on_save_config(self):
        try:
            cfg = self.get_current_config_dict()
            with open("shinseon_backtest_config.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "저장 완료", "현재 백테스터 설정이 'shinseon_backtest_config.json' 파일에 안전하게 저장되었습니다!")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 실패: {e}")

    def apply_config_to_ui(self, data):
        """shinseon_config.json 또는 백테스터 json 데이터를 GUI 위젯들에 100% 자동 매핑"""
        # 1. 탭 1: 세션별 설정 매핑 (session_thresholds 또는 sessions)
        s_map = data.get("session_thresholds") or data.get("sessions") or {}
        for s_key, s_cfg in s_map.items():
            if s_key in self.session_inputs:
                if "enabled" in s_cfg:
                    self.session_inputs[s_key]['enabled'].setChecked(bool(s_cfg["enabled"]))
                if "liq" in s_cfg:
                    self.session_inputs[s_key]['liq'].setText(f"{int(float(s_cfg['liq'])):,}")
                if "oi" in s_cfg:
                    self.session_inputs[s_key]['oi'].setText(f"{float(s_cfg['oi']):.4f}")
                if "sl" in s_cfg:
                    self.session_inputs[s_key]['sl'].setText(f"{float(s_cfg['sl']):.1f}")

        # 2. 탭 2: 트레이딩 핵심 설정 매핑 (session_trading_configs 또는 trading)
        t_map = data.get("session_trading_configs") or data.get("trading") or {}
        for s_key, t_cfg in t_map.items():
            if s_key in self.trading_inputs:
                widgets = self.trading_inputs[s_key]
                if "leverage" in t_cfg and "leverage" in widgets:
                    widgets["leverage"].setText(str(int(float(t_cfg["leverage"]))))
                
                # 비중 1차
                b1 = t_cfg.get("split_entry_1_ratio") or t_cfg.get("buy1_ratio")
                if b1 is not None and "buy1_ratio" in widgets:
                    widgets["buy1_ratio"].setText(str(float(b1)))

                # 비중 2차
                b2 = t_cfg.get("split_entry_2_ratio") or t_cfg.get("buy2_ratio")
                if b2 is not None and "buy2_ratio" in widgets:
                    widgets["buy2_ratio"].setText(str(float(b2)))

                # DCA 하락폭
                dca = t_cfg.get("split_entry_2_trigger_pct") or t_cfg.get("dca_drop")
                if dca is not None and "dca_drop" in widgets:
                    widgets["dca_drop"].setText(str(float(dca)))

                # 추가매수 쿨타임
                dca_t = t_cfg.get("split_cooldown_seconds") or t_cfg.get("dca_time_limit")
                if dca_t is not None and "dca_time_limit" in widgets:
                    widgets["dca_time_limit"].setText(str(float(dca_t)))

                # 손절 쿨타임
                sl_cd = t_cfg.get("cooldown_seconds") or t_cfg.get("sl_cooldown")
                if sl_cd is not None and "sl_cooldown" in widgets:
                    widgets["sl_cooldown"].setText(str(float(sl_cd)))

                # 익절 쿨타임
                tp_cd = t_cfg.get("profit_cooldown_seconds") or t_cfg.get("tp_cooldown")
                if tp_cd is not None and "tp_cooldown" in widgets:
                    widgets["tp_cooldown"].setText(str(float(tp_cd)))

        # 3. 탭 3: 가드레일 설정 매핑 (guardrail_configs 또는 session_guardrails 또는 guardrails)
        g_map = data.get("guardrail_configs") or data.get("session_guardrails") or data.get("guardrails") or {}
        for s_key, g_cfg in g_map.items():
            if isinstance(g_cfg, dict) and s_key in self.guard_inputs:
                widgets = self.guard_inputs[s_key]
                if "tp1" in g_cfg and "tp1" in widgets:
                    widgets["tp1"].setText(f"{float(g_cfg['tp1']):.2f}")
                if "tp2" in g_cfg and "tp2" in widgets:
                    widgets["tp2"].setText(f"{float(g_cfg['tp2']):.2f}")
                if "be_guard" in g_cfg and "be_guard" in widgets:
                    widgets["be_guard"].setText(f"{float(g_cfg['be_guard']):.2f}")

        # 4. 자금 & 수수료
        if "initial_balance" in data:
            self.ed_initial_balance.setText(str(data["initial_balance"]))
        if "fee_rate" in data:
            self.ed_custom_fee.setText(f"{float(data['fee_rate']):.5f}")

    def on_load_config_file(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "설정 파일 불러오기", "shinseon_config.json", "JSON Files (*.json)")
        if not fpath:
            return
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.apply_config_to_ui(data)
            self.on_run_backtest()
            QMessageBox.information(self, "불러오기 완료", f"신선 설정 파일을 성공적으로 불러와 UI에 적용하였습니다:\n{fpath}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 불러오기 실패: {e}")

    def load_config_defaults(self):
        # 1. 날짜 기본값
        self.set_date_preset("full")
        # 2. 로컬 shinseon_config.json이 존재하면 자동 로드
        if os.path.exists("shinseon_config.json"):
            try:
                with open("shinseon_config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.apply_config_to_ui(data)
            except Exception:
                pass
        # 3. 1회 백테스트 실행
        self.on_run_backtest()

def main():
    app = QApplication(sys.argv)
    window = ShinseonBacktesterGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
