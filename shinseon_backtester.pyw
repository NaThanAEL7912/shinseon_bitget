# -*- coding: utf-8 -*-
"""
신선(SHINSEON) 오더플로우 전문 독립 전략 백테스터 GUI (ShinSeon Strategy Backtester V7.72)
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
from PySide6.QtCore import Qt, QDateTime, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QIcon

from backtest_engine import run_backtest_simulation, load_all_session_data, sync_and_build_all_data, get_unified_ticks_cached

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
        self.setWindowTitle("신선(神選) 오더플로우 전문 독립 전략 백테스터 V7.72 [SHINSEON BACKTESTER]")
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
        title_lbl = QLabel("<b style='font-size: 16px; color: #ffd700;'>神選 [SHINSEON] 전략 백테스터</b> <span style='color: #8b949e;'>V7.72 (기획서 369 삼위일체 3대 AND 오더플로우 연동)</span>")
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
        date_h.setSpacing(8)

        date_h.addWidget(QLabel("<b style='color: #00ffcc;'>시작 일시:</b>"))
        self.dt_start = QDateTimeEdit(QDateTime.fromString("2026-08-17 00:00:00", "yyyy-MM-dd HH:mm:ss"))
        self.dt_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_start.setMinimumDateTime(QDateTime.fromString("2026-08-01 00:00:00", "yyyy-MM-dd HH:mm:ss"))
        self.dt_start.setMaximumDateTime(QDateTime.fromString("2026-08-31 23:59:59", "yyyy-MM-dd HH:mm:ss"))
        self.dt_start.setCalendarPopup(True)
        self.dt_start.dateTimeChanged.connect(self.update_period_preview)
        date_h.addWidget(self.dt_start)

        date_h.addWidget(QLabel("<b style='color: #ff3366;'>종료 일시:</b>"))
        self.dt_end = QDateTimeEdit(QDateTime.fromString("2026-08-21 23:59:59", "yyyy-MM-dd HH:mm:ss"))
        self.dt_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_end.setMinimumDateTime(QDateTime.fromString("2026-08-01 00:00:00", "yyyy-MM-dd HH:mm:ss"))
        self.dt_end.setMaximumDateTime(QDateTime.fromString("2026-08-31 23:59:59", "yyyy-MM-dd HH:mm:ss"))
        self.dt_end.setCalendarPopup(True)
        self.dt_end.dateTimeChanged.connect(self.update_period_preview)
        date_h.addWidget(self.dt_end)

        # 빠른 프리셋 버튼들
        btn_full = QPushButton("전체 기간")
        btn_full.setObjectName("btn_preset")
        btn_full.clicked.connect(lambda: self.set_date_preset("full"))
        date_h.addWidget(btn_full)

        btn_3d = QPushButton("최근 3일")
        btn_3d.setObjectName("btn_preset")
        btn_3d.clicked.connect(lambda: self.set_date_preset("3d"))
        date_h.addWidget(btn_3d)

        btn_weekday = QPushButton("지난 주 평일 (8/17~8/21)")
        btn_weekday.setObjectName("btn_preset")
        btn_weekday.setStyleSheet("color: #00ffcc; font-weight: bold;")
        btn_weekday.clicked.connect(lambda: self.set_date_preset("weekday"))
        date_h.addWidget(btn_weekday)

        btn_weekend = QPushButton("주말 (8/22~8/23)")
        btn_weekend.setObjectName("btn_preset")
        btn_weekend.setStyleSheet("color: #ff9900; font-weight: bold;")
        btn_weekend.clicked.connect(lambda: self.set_date_preset("weekend"))
        date_h.addWidget(btn_weekend)

        btn_24h = QPushButton("최근 24시간")
        btn_24h.setObjectName("btn_preset")
        btn_24h.clicked.connect(lambda: self.set_date_preset("24h"))
        date_h.addWidget(btn_24h)

        # ⚡ 최신 데이터 정렬 버튼
        self.btn_sync_data = QPushButton("⚡ 최신 실측 데이터 정렬 (Sync)")
        self.btn_sync_data.setStyleSheet("""
            QPushButton {
                background-color: #004d40;
                color: #00ffcc;
                border: 1px solid #00ffcc;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 900;
            }
            QPushButton:hover {
                background-color: #00796b;
                color: #ffffff;
            }
        """)
        self.btn_sync_data.clicked.connect(self.on_sync_data)
        date_h.addWidget(self.btn_sync_data)

        # 선택 기간 실시간 안내 라벨
        self.lbl_period_preview = QLabel("<b>[📌 선택 구간: 08/17 ~ 08/21]</b>")
        self.lbl_period_preview.setStyleSheet("color: #ffd700; font-size: 13px; font-weight: bold; margin-left: 10px;")
        date_h.addWidget(self.lbl_period_preview)

        date_h.addStretch()
        layout.addLayout(date_h)

        return group

    def on_sync_data(self):
        """downloads 폴더 내의 모든 실측 CSV를 전수 스캔하여 pkl 캐시 갱신 및 날짜 범위 자동 확장 (사용자 선택 날짜 100% 보존)"""
        try:
            # 1. 정렬 전 폐하께서 선택해두신 날짜 범위 안전 기억
            cur_start_dt, cur_end_dt = self.get_selected_date_range()

            self.btn_sync_data.setText("⏳ 데이터 정렬 중...")
            self.btn_sync_data.setEnabled(False)
            QApplication.processEvents()

            res = sync_and_build_all_data()
            if not res.get('success'):
                QMessageBox.critical(self, "오류", f"데이터 정렬 실패: {res.get('error')}")
                return

            min_dt = res['min_dt']
            max_dt = res['max_dt']
            total_files = res['total_files']
            total_ticks = res['total_ticks']

            # 2. 폐하의 선택 날짜를 100% 철통 보존 (전체 날짜로 덮어쓰기 방지)
            if cur_start_dt and cur_end_dt:
                self.dt_start.setDateTime(QDateTime(cur_start_dt.year, cur_start_dt.month, cur_start_dt.day, cur_start_dt.hour, cur_start_dt.minute, cur_start_dt.second))
                self.dt_end.setDateTime(QDateTime(cur_end_dt.year, cur_end_dt.month, cur_end_dt.day, cur_end_dt.hour, cur_end_dt.minute, cur_end_dt.second))
            else:
                self.dt_start.setDateTime(QDateTime(min_dt.year, min_dt.month, min_dt.day, min_dt.hour, min_dt.minute, min_dt.second))
                self.dt_end.setDateTime(QDateTime(max_dt.year, max_dt.month, max_dt.day, max_dt.hour, max_dt.minute, max_dt.second))

            QMessageBox.information(
                self,
                "데이터 정렬 완료",
                f"총 {total_files}개 폴더/파일의 실측 데이터 ({total_ticks:,}틱)가 성공적으로 정렬되었습니다!\n\n"
                f"📅 전체 가용 기간: {min_dt.strftime('%Y-%m-%d %H:%M')} ~ {max_dt.strftime('%Y-%m-%d %H:%M')}\n"
                f"🎯 현재 선택 유지 구간: {cur_start_dt.strftime('%Y-%m-%d %H:%M')} ~ {cur_end_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"선택하신 구간으로 백테스트가 연계 수행됩니다!"
            )

            # 즉시 1회 백테스트 실행 (선택된 구간으로 정밀 실행)
            self.on_run_backtest()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 정렬 중 예외 발생: {e}")
        finally:
            self.btn_sync_data.setText("⚡ 최신 실측 데이터 정렬 (Sync)")
            self.btn_sync_data.setEnabled(True)


    def update_period_preview(self):
        """사용자가 날짜를 변경할 때 실시간으로 선택 기간 안내 라벨 갱신"""
        try:
            s_dt, e_dt = self.get_selected_date_range()
            diff = e_dt - s_dt
            days = diff.days + (1 if diff.seconds > 0 else 0)
            if hasattr(self, 'lbl_period_preview'):
                self.lbl_period_preview.setText(f"<b>[📌 선택 구간: {s_dt.strftime('%m/%d')} ~ {e_dt.strftime('%m/%d')} (총 {max(1, days)}일간)]</b>")
        except Exception:
            pass

    def set_date_preset(self, preset):
        # RAM 캐시 데이터에서 min/max 초광속(0.0001초) 참조
        _, all_ts = get_unified_ticks_cached()
        if all_ts:
            min_dt = datetime.fromtimestamp(all_ts[0])
            max_dt = datetime.fromtimestamp(all_ts[-1])
        else:
            min_dt = datetime(2026, 8, 7, 6, 15, 5)
            max_dt = datetime(2026, 8, 24, 2, 31, 1)

        if preset == "full":
            self.dt_start.setDateTime(QDateTime(min_dt.year, min_dt.month, min_dt.day, 0, 0, 0))
            self.dt_end.setDateTime(QDateTime(max_dt.year, max_dt.month, max_dt.day, 23, 59, 59))
        elif preset == "24h":
            start_24h = max_dt - timedelta(hours=24)
            self.dt_start.setDateTime(QDateTime(start_24h.year, start_24h.month, start_24h.day, start_24h.hour, start_24h.minute, start_24h.second))
            self.dt_end.setDateTime(QDateTime(max_dt.year, max_dt.month, max_dt.day, 23, 59, 59))
        elif preset == "3d":
            start_3d = max_dt - timedelta(days=2) # 3일간
            self.dt_start.setDateTime(QDateTime(start_3d.year, start_3d.month, start_3d.day, 0, 0, 0))
            self.dt_end.setDateTime(QDateTime(max_dt.year, max_dt.month, max_dt.day, 23, 59, 59))
        elif preset == "weekday":
            # 지난 주 평일 5일간 (8/17 월 00:00:00 ~ 8/21 금 23:59:59)
            self.dt_start.setDateTime(QDateTime(2026, 8, 17, 0, 0, 0))
            self.dt_end.setDateTime(QDateTime(2026, 8, 21, 23, 59, 59))
        elif preset == "weekend":
            # 주말 2일간 (8/22 토 00:00:00 ~ 8/23 일 23:59:59)
            self.dt_start.setDateTime(QDateTime(2026, 8, 22, 0, 0, 0))
            self.dt_end.setDateTime(QDateTime(2026, 8, 23, 23, 59, 59))

        self.update_period_preview()


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
            h_row.addWidget(QLabel("<b>분할익절 가동</b>"), 1, Qt.AlignCenter)
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

                chk_half = QCheckBox()
                chk_half.setChecked(True)
                chk_half.setStyleSheet("margin-left: 15px;")
                row.addWidget(chk_half, 1, Qt.AlignCenter)

                self.guard_inputs[key] = {
                    'tp1': ed_tp1,
                    'tp2': ed_tp2,
                    'be_guard': ed_be,
                    'enabled': chk_half
                }
                layout_grp.addLayout(row)

            g_layout.addWidget(grp)

        # 공통 가드레일 및 불타기 / 보존가드 설정
        c_grp = QGroupBox("공통 분할 익절 & 추세 추종 불타기 & 보존가드 설정")
        c_layout = QVBoxLayout(c_grp)
        c_layout.setSpacing(10)

        # 1행: 1차 / 2차 분할익절 비율
        row_split = QHBoxLayout()
        row_split.addWidget(QLabel("1차 분할 익절 비율 (%):"), 2)
        self.ed_tp1_split = QLineEdit("50.0")
        self.ed_tp1_split.setAlignment(Qt.AlignCenter)
        row_split.addWidget(self.ed_tp1_split, 2)

        row_split.addWidget(QLabel("2차 분할 익절 비율 (%):"), 2)
        self.ed_tp2_split = QLineEdit("50.0")
        self.ed_tp2_split.setAlignment(Qt.AlignCenter)
        row_split.addWidget(self.ed_tp2_split, 2)
        c_layout.addLayout(row_split)

        # 2행: 추세 추종 불타기 (Pyramiding) 가동
        row_pyra = QHBoxLayout()
        self.chk_pyramiding = QCheckBox("추세 추종 불타기(Pyramiding) 가동")
        self.chk_pyramiding.setChecked(True)
        self.chk_pyramiding.setStyleSheet("color: #ffd700; font-weight: bold;")
        row_pyra.addWidget(self.chk_pyramiding, 4)

        self.ed_pyramiding_ratio = QLineEdit("30.0")
        self.ed_pyramiding_ratio.setAlignment(Qt.AlignCenter)
        row_pyra.addWidget(self.ed_pyramiding_ratio, 2)
        row_pyra.addStretch(2)
        c_layout.addLayout(row_pyra)

        # 3행: 보존가드 발동 최소값 & 가드레일 스탑값
        row_guard = QHBoxLayout()
        row_guard.addWidget(QLabel("🛡️ 보존가드 발동 최소값 (PnL %):"), 3)
        self.ed_mid_guard_trigger = QLineEdit("0.60")
        self.ed_mid_guard_trigger.setAlignment(Qt.AlignCenter)
        row_guard.addWidget(self.ed_mid_guard_trigger, 2)

        row_guard.addWidget(QLabel("가드레일 스탑값 (PnL %):"), 3)
        self.ed_mid_guard_offset = QLineEdit("0.20")
        self.ed_mid_guard_offset.setAlignment(Qt.AlignCenter)
        row_guard.addWidget(self.ed_mid_guard_offset, 2)
        c_layout.addLayout(row_guard)

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
        self.cb_fee_preset.addItem("👑 비트겟 일반 레퍼럴 (0.040% / 0.00040)", 0.00040)
        self.cb_fee_preset.addItem("🔥 박호두 레퍼럴 50% 할인 (0.030% / 0.00030)", 0.00030)
        self.cb_fee_preset.addItem("비트겟 기본 표준 시장가 (0.060% / 0.00060)", 0.00060)
        self.cb_fee_preset.addItem("VIP / 페이백 결합 최상위 (0.025% / 0.00025)", 0.00025)
        self.cb_fee_preset.addItem("수수료 0% (수수료 미차감 원장 분석)", 0.00000)
        self.cb_fee_preset.currentIndexChanged.connect(self.on_fee_preset_changed)
        row_f.addWidget(self.cb_fee_preset, 3)

        self.ed_custom_fee = QLineEdit("0.00040")
        self.ed_custom_fee.setAlignment(Qt.AlignCenter)
        self.ed_custom_fee.textChanged.connect(self.on_custom_fee_text_changed)
        row_f.addWidget(self.ed_custom_fee, 1)
        row_f.addStretch(1)
        g_layout.addLayout(row_f)

        layout.addWidget(grp)
        layout.addStretch()
        return widget

    def on_fee_preset_changed(self, idx):
        val = self.cb_fee_preset.currentData()
        if val is not None:
            self.ed_custom_fee.blockSignals(True)
            self.ed_custom_fee.setText(f"{val:.5f}")
            self.ed_custom_fee.blockSignals(False)

    def on_custom_fee_text_changed(self, text):
        try:
            val = float(text.strip())
            for i in range(self.cb_fee_preset.count()):
                c_val = self.cb_fee_preset.itemData(i)
                if abs(c_val - val) < 1e-6:
                    self.cb_fee_preset.blockSignals(True)
                    self.cb_fee_preset.setCurrentIndex(i)
                    self.cb_fee_preset.blockSignals(False)
                    return
        except Exception:
            pass


    # -------------------------------------------------------------
    # 6. 하단 결과 대시보드 (종합 요약 + 세션별 성과 + 거래 일지)
    # -------------------------------------------------------------
    def create_results_dashboard(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # 8대 요약 카드 박스
        self.cards_grp = QGroupBox("📊 백테스팅 종합 성과 대시보드 (Performance Summary)")
        cards_layout = QHBoxLayout(self.cards_grp)
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

        layout.addWidget(self.cards_grp)

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
    def get_selected_date_range(self):
        """키보드 포커스 미커밋 방지 및 텍스트 직접 파싱 2중 안전망을 통한 정밀 날짜 추출 (2026년 락 & 역전 자동 보정)"""
        import re
        self.dt_start.interpretText()
        self.dt_end.interpretText()
        
        # 1. 텍스트 직접 정제 및 파싱
        s_txt = self.dt_start.text().strip()
        e_txt = self.dt_end.text().strip()
        
        # 특수문자/LTR/RTL 마크 정제 (숫자, -, :, 공백만 추출)
        s_txt_clean = re.sub(r'[^0-9\-:\s]', '', s_txt).strip()
        e_txt_clean = re.sub(r'[^0-9\-:\s]', '', e_txt).strip()
        
        # 연도 튐 방지: 2027년 등 엉뚱한 연도가 오면 2026년으로 자동 교정
        if s_txt_clean.startswith("2027-"):
            s_txt_clean = "2026-" + s_txt_clean[5:]
        if e_txt_clean.startswith("2027-"):
            e_txt_clean = "2026-" + e_txt_clean[5:]
        
        start_dt = None
        end_dt = None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
            if not start_dt:
                try: start_dt = datetime.strptime(s_txt_clean, fmt)
                except Exception: pass
            if not end_dt:
                try: end_dt = datetime.strptime(e_txt_clean, fmt)
                except Exception: pass
                
        if not start_dt:
            start_dt = self.dt_start.dateTime().toPython()
        if not end_dt:
            end_dt = self.dt_end.dateTime().toPython()
            
        # 연도 강제 2026년 락
        if start_dt.year != 2026:
            try: start_dt = start_dt.replace(year=2026)
            except Exception: pass
        if end_dt.year != 2026:
            try: end_dt = end_dt.replace(year=2026)
            except Exception: pass

        # 시작일 > 종료일 역전 자동 보정
        if start_dt > end_dt:
            end_dt = datetime(start_dt.year, start_dt.month, start_dt.day, 23, 59, 59)
            
        return start_dt, end_dt

    def get_current_config_dict(self):
        start_dt, end_dt = self.get_selected_date_range()
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
            'tp2_split_ratio': float(self.ed_tp2_split.text().strip()),
            'pyramiding_enabled': self.chk_pyramiding.isChecked(),
            'pyramiding_ratio': float(self.ed_pyramiding_ratio.text().strip()),
            'mid_guard_trigger': float(self.ed_mid_guard_trigger.text().strip()),
            'mid_guard_offset': float(self.ed_mid_guard_offset.text().strip())
        }
        for s_k, g_dict in self.guard_inputs.items():
            guard_dict[s_k] = {
                'tp1': float(g_dict['tp1'].text().strip()),
                'tp2': float(g_dict['tp2'].text().strip()),
                'be_guard': float(g_dict['be_guard'].text().strip()),
                'enabled': g_dict['enabled'].isChecked()
            }

        return {
            'start_date': start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            'end_date': end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            'initial_balance': float(self.ed_initial_balance.text().strip()),
            'fee_rate': float(self.ed_custom_fee.text().strip()),
            'sessions': sessions_dict,
            'trading': trading_dict,
            'guardrails': guard_dict
        }

    def on_run_backtest(self):
        try:
            # 1. 포커스 강제 커밋 및 정밀 날짜 추출
            start_dt, end_dt = self.get_selected_date_range()

            # 계산 중 시각적 로딩 상태 전환 (즉시 반응)
            self.btn_run.setText(f"⏳ {start_dt.strftime('%m/%d')}~{end_dt.strftime('%m/%d')} 실측 오더플로우 정밀 연산 중...")
            self.btn_run.setEnabled(False)
            self.btn_run.setStyleSheet("background-color: #d97706; color: #ffffff; border: 1px solid #fbbf24; font-weight: bold; border-radius: 6px; padding: 6px 14px;")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            if hasattr(self, 'cards_grp'):
                self.cards_grp.setTitle(f"⏳ 백테스팅 정밀 시뮬레이션 계산 중... ({start_dt.strftime('%Y-%m-%d %H:%M')} ~ {end_dt.strftime('%Y-%m-%d %H:%M')})")
            
            QApplication.processEvents() # 즉시 1프레임 렌더링

            # 2. 연산 수행
            cfg = self.get_current_config_dict()
            res = run_backtest_simulation(cfg, start_dt, end_dt)
            if 'error' in res:
                QMessageBox.critical(self, "오류", res['error'])
                return

            self.last_results = res
            self.render_results(res)
            if hasattr(self, 'cards_grp'):
                self.cards_grp.setTitle(f"📊 백테스팅 성과 대시보드 [분석 기간: {start_dt.strftime('%Y-%m-%d %H:%M')} ~ {end_dt.strftime('%Y-%m-%d %H:%M')}]")
        except Exception as e:
            QMessageBox.critical(self, "백테스트 예외", f"시뮬레이션 실행 중 오류 발생: {e}")
        finally:
            # 3. 완료 후 원래 버튼 상태로 자동 복원
            self.btn_run.setText("🚀 백테스트 실행 (Run Backtest)")
            self.btn_run.setEnabled(True)
            self.btn_run.setStyleSheet("")
            QApplication.restoreOverrideCursor()



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
            # 1. UI 최신 데이터 추출
            cfg = self.get_current_config_dict()

            # 2. 백테스터 전용 설정 파일 원클릭 즉시 저장 (실전 봇 shinseon_config.json과는 100% 완전 격리!)
            backtest_cfg_file = "shinseon_backtest_config.json"
            with open(backtest_cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "저장 완료", "백테스터 전용 설정(shinseon_backtest_config.json)이 안전하게 저장되었습니다!\n(실전 봇 설정에는 일체 영향을 주지 않습니다)")
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
        # 대문자 키 매핑
        guard_rev_map = {
            "ASIA": "asia", "LONDON": "europe", "NY": "us", "PACIFIC": "pacific",
            "WEEKEND_ASIA": "weekend_asia", "WEEKEND_LONDON": "weekend_europe",
            "WEEKEND_NY": "weekend_us", "WEEKEND_PACIFIC": "weekend_pacific"
        }
        for s_key, g_cfg in g_map.items():
            norm_key = guard_rev_map.get(s_key, s_key)
            if isinstance(g_cfg, dict) and norm_key in self.guard_inputs:
                widgets = self.guard_inputs[norm_key]
                if "trigger" in g_cfg and "tp1" in widgets:
                    widgets["tp1"].setText(f"{float(g_cfg['trigger']):.2f}")
                elif "tp1" in g_cfg and "tp1" in widgets:
                    widgets["tp1"].setText(f"{float(g_cfg['tp1']):.2f}")

                if "trigger_2" in g_cfg and "tp2" in widgets:
                    widgets["tp2"].setText(f"{float(g_cfg['trigger_2']):.2f}")
                elif "tp2" in g_cfg and "tp2" in widgets:
                    widgets["tp2"].setText(f"{float(g_cfg['tp2']):.2f}")

                if "guard" in g_cfg and "be_guard" in widgets:
                    widgets["be_guard"].setText(f"{float(g_cfg['guard']):.2f}")
                elif "be_guard" in g_cfg and "be_guard" in widgets:
                    widgets["be_guard"].setText(f"{float(g_cfg['be_guard']):.2f}")

                if "enabled" in g_cfg and "enabled" in widgets:
                    widgets["enabled"].setChecked(bool(g_cfg["enabled"]))

        # 공통 분할 익절 비율 복원
        tp1_s = data.get("tp1_split_ratio") or (g_map.get("tp1_split_ratio") if isinstance(g_map, dict) else None) or data.get("half_exit_close_ratio")
        if tp1_s is not None:
            self.ed_tp1_split.setText(f"{float(tp1_s):.1f}")
        tp2_s = data.get("tp2_split_ratio") or (g_map.get("tp2_split_ratio") if isinstance(g_map, dict) else None) or data.get("half_exit_close_ratio_2")
        if tp2_s is not None:
            self.ed_tp2_split.setText(f"{float(tp2_s):.1f}")

        # 추세 추종 불타기 (Pyramiding) 복원
        pyra_en = data.get("pyramiding_enabled") or (g_map.get("pyramiding_enabled") if isinstance(g_map, dict) else None)
        if pyra_en is not None:
            self.chk_pyramiding.setChecked(bool(pyra_en))
        pyra_rat = data.get("pyramiding_ratio") or (g_map.get("pyramiding_ratio") if isinstance(g_map, dict) else None)
        if pyra_rat is not None:
            self.ed_pyramiding_ratio.setText(f"{float(pyra_rat):.1f}")

        # 중간 보존 가드 복원
        mid_trig = data.get("mid_guard_trigger") or (g_map.get("mid_guard_trigger") if isinstance(g_map, dict) else None)
        if mid_trig is not None:
            self.ed_mid_guard_trigger.setText(f"{float(mid_trig):.2f}")
        mid_off = data.get("mid_guard_offset") or (g_map.get("mid_guard_offset") if isinstance(g_map, dict) else None)
        if mid_off is not None:
            self.ed_mid_guard_offset.setText(f"{float(mid_off):.2f}")

        # 4. 자금 & 수수료
        if "initial_balance" in data:
            self.ed_initial_balance.setText(str(data["initial_balance"]))
        if "fee_rate" in data:
            fr = float(data['fee_rate'])
            self.ed_custom_fee.setText(f"{fr:.5f}")
            self.on_custom_fee_text_changed(f"{fr:.5f}")

        # 5. 상단 시작/종료 일시 복원
        if "start_date" in data:
            try:
                dt_s = QDateTime.fromString(data["start_date"], "yyyy-MM-dd HH:mm:ss")
                if dt_s.isValid():
                    self.dt_start.setDateTime(dt_s)
            except Exception:
                pass
        if "end_date" in data:
            try:
                dt_e = QDateTime.fromString(data["end_date"], "yyyy-MM-dd HH:mm:ss")
                if dt_e.isValid():
                    self.dt_end.setDateTime(dt_e)
            except Exception:
                pass

    def on_load_config_file(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "설정 파일 불러오기", "shinseon_backtest_config.json", "JSON Files (*.json)")
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
        # 1. 날짜 기본값 (초고속 시동을 위해 최근 3일 기본 세팅)
        self.set_date_preset("3d")
        # 2. 수수료율 기본값 (비트겟 0.040% / 0.00040)
        self.ed_custom_fee.setText("0.00040")
        self.on_custom_fee_text_changed("0.00040")
        
        # 3. 1순위: 사용자가 마지막으로 저장한 백테스터 전용 설정 로드
        loaded = False
        if os.path.exists("shinseon_backtest_config.json"):
            try:
                with open("shinseon_backtest_config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.apply_config_to_ui(data)
                loaded = True
            except Exception:
                loaded = False

        # 4. 2순위: 백테스트 설정이 없을 경우 실전 shinseon_config.json 로드
        if not loaded and os.path.exists("shinseon_config.json"):
            try:
                with open("shinseon_config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.apply_config_to_ui(data)
            except Exception:
                pass

        # 5. 창이 먼저 즉각 뜬 후(0.05초) 비동기로 1회 백테스트 가동
        QTimer.singleShot(50, self.on_run_backtest)

def main():
    app = QApplication(sys.argv)
    window = ShinseonBacktesterGUI()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
