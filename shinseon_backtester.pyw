import os
import sys
import csv
import time
from datetime import datetime
import random

from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QListWidget, QListWidgetItem, QTabWidget, QGroupBox,
    QMessageBox, QSplitter, QProgressBar, QCheckBox, QGridLayout
)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPalette, QPainter, QPen, QBrush

# ==============================================================================
# 테마 스타일 정의 (임페리얼 다크 골드)
# ==============================================================================
DARK_THEME_STYLE = """
    QMainWindow {
        background-color: #121212;
    }
    QWidget {
        background-color: #121212;
        color: #FFFFFF;
        font-family: 'Malgun Gothic', sans-serif;
    }
    QGroupBox {
        border: 1px solid #332A20;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 15px;
        font-weight: bold;
        color: #DEBA9D;
        background-color: #1A1816;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
    QLabel {
        color: #E2DDD9;
        font-size: 12px;
        background-color: transparent;
    }
    QLineEdit {
        background-color: #242220;
        border: 1px solid #4D3F30;
        border-radius: 4px;
        color: #FFFFFF;
        padding: 5px;
        font-size: 12px;
    }
    QLineEdit:focus {
        border: 1px solid #8C7355;
        background-color: #2D2A27;
    }
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8C7355, stop:1 #594733);
        color: #F5EFEB;
        font-weight: bold;
        font-size: 12px;
        border: 1px solid #735D43;
        border-radius: 4px;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A18663, stop:1 #8C7355);
    }
    QPushButton:pressed {
        background: #4A3A28;
    }
    QPushButton:disabled {
        background: #242220;
        color: #666666;
        border: 1px solid #333333;
    }
    QTableWidget {
        background-color: #161514;
        border: 1px solid #332A20;
        gridline-color: #2D2A27;
        font-size: 11px;
    }
    QTableWidget::item {
        padding: 4px;
    }
    QTableWidget::item:selected {
        background-color: #4A3A28;
        color: #FFFFFF;
    }
    QHeaderView::section {
        background-color: #242220;
        color: #DEBA9D;
        border: 1px solid #332A20;
        padding: 4px;
        font-weight: bold;
        font-size: 11px;
    }
    QListWidget {
        background-color: #161514;
        border: 1px solid #332A20;
        border-radius: 4px;
    }
    QListWidget::item {
        padding: 6px;
        border-bottom: 1px solid #242220;
    }
    QListWidget::item:hover {
        background-color: #242220;
    }
    QListWidget::item:selected {
        background-color: #4A3A28;
        color: #FFFFFF;
    }
    QTabWidget::pane {
        border: 1px solid #332A20;
        background-color: #1A1816;
        border-radius: 6px;
    }
    QTabBar::tab {
        background: #1C1A18;
        border: 1px solid #332A20;
        border-bottom-color: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 8px 16px;
        color: #A18663;
        font-weight: bold;
    }
    QTabBar::tab:selected {
        background: #1A1816;
        color: #FFFFFF;
        border-bottom: 2px solid #8C7355;
    }
    QProgressBar {
        border: 1px solid #332A20;
        border-radius: 4px;
        text-align: center;
        background-color: #161514;
    }
    QProgressBar::chunk {
        background-color: #8C7355;
    }
    QCheckBox {
        color: #E2DDD9;
        font-size: 12px;
        background-color: transparent;
    }
    QCheckBox::indicator {
        width: 15px;
        height: 15px;
    }
"""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "docs", "historical_data")

# ==============================================================================
# 세션 계산 유틸리티 함수 (KST 기준)
# ==============================================================================
def get_session_key(time_str):
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        minute = dt.minute
        if 9 <= hour < 16:
            return "asia"
        elif 16 <= hour < 22 or (hour == 22 and minute < 30):
            return "europe"
        elif (hour == 22 and minute >= 30) or hour >= 23 or hour < 5:
            return "us"
        else:
            return "pacific"
    except Exception:
        return "asia"

def get_session_name(session_key):
    if session_key == "asia":
        return "🔴 아시아"
    elif session_key == "europe":
        return "🟡 유럽"
    elif session_key == "us":
        return "🟢 미국"
    elif session_key == "pacific":
        return "⚪ 태평양"
    return "알 수 없음"

# ==============================================================================
# QPainter 기반 실시간 에쿼티 커브(자산 곡선) 위젯
# ==============================================================================
class EquityChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #0E0D0C; border: 1px solid #242220; border-radius: 4px;")

    def set_data(self, points):
        # points: list of floats representing cumulative return (%)
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 배경 그리기
        painter.setBrush(QBrush(QColor("#0E0D0C")))
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, width, height)
        
        if not self.points:
            painter.setPen(QColor("#555555"))
            painter.drawText(self.rect(), Qt.AlignCenter, "시뮬레이션 데이터가 없습니다.")
            return

        # 마진 정의
        margin_left = 40
        margin_right = 15
        margin_top = 15
        margin_bottom = 20
        
        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom
        
        min_y = min(self.points)
        max_y = max(self.points)
        
        # 여유 공간 확보
        if max_y == min_y:
            max_y += 1.0
            min_y -= 1.0
        else:
            diff = max_y - min_y
            max_y += diff * 0.1
            min_y -= diff * 0.1
            
        n = len(self.points)
        
        # 그리드 가이드라인 그리기
        painter.setPen(QPen(QColor("#242220"), 1, Qt.DashLine))
        # 0% 가이드라인
        if min_y < 0.0 < max_y:
            zero_y = margin_top + plot_h - int(((0.0 - min_y) / (max_y - min_y)) * plot_h)
            painter.drawText(5, zero_y + 4, "0.0%")
            painter.drawLine(margin_left, zero_y, width - margin_right, zero_y)
            
        # 상단/하단 라벨 그리기
        painter.setPen(QPen(QColor("#888888"), 1))
        painter.drawText(5, margin_top + 10, f"{max_y:+.2f}%")
        painter.drawText(5, height - margin_bottom - 2, f"{min_y:+.2f}%")
        
        # 테두리 축선
        painter.setPen(QPen(QColor("#332A20"), 1))
        painter.drawLine(margin_left, margin_top, margin_left, height - margin_bottom)
        painter.drawLine(margin_left, height - margin_bottom, width - margin_right, height - margin_bottom)
        
        # 에쿼티 라인 그리기
        pen = QPen(QColor("#DEBA9D"), 2, Qt.SolidLine)
        painter.setPen(pen)
        
        prev_x = None
        prev_y = None
        
        for i, val in enumerate(self.points):
            x = margin_left + int((i / (n - 1)) * plot_w) if n > 1 else margin_left
            y = margin_top + plot_h - int(((val - min_y) / (max_y - min_y)) * plot_h)
            
            if prev_x is not None:
                painter.drawLine(prev_x, prev_y, x, y)
                
            prev_x = x
            prev_y = y

# ==============================================================================
# 백테스팅 시뮬레이션 및 그리드 최적화 백그라운드 스레드
# ==============================================================================
class SessionConfigEditDialog(QDialog):
    def __init__(self, session_thresholds, parent=None):
        super().__init__(parent)
        self.session_thresholds = session_thresholds
        self.init_ui()
        
    def init_ui(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton
        self.setWindowTitle("⚙️ 세션별 설정값 상세 편집 (실전 봇 연동)")
        self.resize(480, 240)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        grid = QGridLayout()
        grid.setSpacing(8)
        
        # Headers
        grid.addWidget(QLabel("세션 구분"), 0, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("1분 누적 청산액 ($)"), 0, 1, Qt.AlignCenter)
        grid.addWidget(QLabel("1분 OI속도 (%)"), 0, 2, Qt.AlignCenter)
        grid.addWidget(QLabel("최초 손절선 (%)"), 0, 3, Qt.AlignCenter)
        
        self.fields = {}
        sessions_info = [
            ("asia", "아시아"),
            ("europe", "유럽"),
            ("us", "미국 본장"),
            ("pacific", "태평양 횡보")
        ]
        
        for idx, (s_key, s_name) in enumerate(sessions_info, start=1):
            lbl = QLabel(s_name)
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, idx, 0)
            
            edit_liq = QLineEdit()
            edit_oi = QLineEdit()
            edit_sl = QLineEdit()
            
            edit_liq.setAlignment(Qt.AlignCenter)
            edit_oi.setAlignment(Qt.AlignCenter)
            edit_sl.setAlignment(Qt.AlignCenter)
            
            s_data = self.session_thresholds.get(s_key, {})
            liq_val = s_data.get("liq", 400000.0)
            edit_liq.setText(f"{int(liq_val):,}")
            edit_oi.setText(str(s_data.get("oi", 0.08)))
            edit_sl.setText(str(s_data.get("sl", -1.0)))
            
            grid.addWidget(edit_liq, idx, 1)
            grid.addWidget(edit_oi, idx, 2)
            grid.addWidget(edit_sl, idx, 3)
            
            self.fields[s_key] = {"liq": edit_liq, "oi": edit_oi, "sl": edit_sl}
            
        layout.addLayout(grid)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("적용 및 저장")
        self.btn_cancel = QPushButton("취소")
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

class BacktestWorker(QThread):
    progress_signal = Signal(int)
    finished_signal = Signal(dict)
    
    def __init__(self, selected_files, target_liq, target_oi, stop_loss, is_optimizer=False, opt_ranges=None, allowed_sessions=None,
                 split_1_ratio=250.0, split_2_ratio=200.0, split_2_trigger_pct=-0.005, cooldown_seconds=300.0,
                 use_config_thresholds=False, session_thresholds=None):
        super().__init__()
        self.selected_files = selected_files
        self.target_liq = target_liq
        self.target_oi = target_oi
        self.stop_loss = stop_loss
        self.is_optimizer = is_optimizer
        self.opt_ranges = opt_ranges # {'liq': [...], 'oi': [...], 'sl': [...]}
        self.allowed_sessions = allowed_sessions or ['asia', 'europe', 'us', 'pacific']
        self.split_1_ratio = split_1_ratio
        self.split_2_ratio = split_2_ratio
        self.split_2_trigger_pct = split_2_trigger_pct
        self.cooldown_seconds = cooldown_seconds
        self.use_config_thresholds = use_config_thresholds
        self.session_thresholds = session_thresholds
        
    def run(self):
        # 1. 파일 데이터 일괄 로드
        all_data = []
        for file_path in self.selected_files:
            if not os.path.exists(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    reader = csv.reader(f)
                    header = next(reader) # skip header
                    for row in reader:
                        if len(row) >= 4:
                            # 시간, 가격, 청산, OI속도
                            try:
                                all_data.append({
                                    'time_str': row[0].strip(),
                                    'price': float(row[1]),
                                    'liq': float(row[2]),
                                    'oi_speed': float(row[3])
                                })
                            except Exception:
                                pass
            except Exception:
                pass
                
        # 시간에 따른 정렬
        all_data.sort(key=lambda x: x['time_str'])
        
        if not all_data:
            self.finished_signal.emit({"success": False, "error": "지정된 파일에서 시뮬레이션 가능한 유효 데이터를 읽어들이지 못했습니다."})
            return
            
        if self.is_optimizer:
            self.run_grid_optimization(all_data)
        else:
            self.run_single_backtest(all_data, self.target_liq, self.target_oi, self.stop_loss)

    def run_single_backtest(self, all_data, target_liq, target_oi, stop_loss_pct):
        # 시뮬레이션 매개변수 초기화
        is_in_position = False
        has_second_entry = False
        position_direction = None # "LONG" or "SHORT"
        entry_price_1 = 0.0
        entry_price_2 = 0.0
        entry_price = 0.0 # 가중 평균 평단
        entry_time = ""
        peak_pnl = 0.0
        
        trades = []
        equity_curve = [0.0] # 누적 수익률 곡선 (%)
        cumulative_pnl = 0.0
        
        price_history = []
        total_rows = len(all_data)
        
        # 쿨다운 제한 시점 타임스탬프 (초 단위)
        cooldown_until_ts = -999999.0
        last_entry_ts = -999999.0
        
        for idx, row in enumerate(all_data):
            if idx % max(1, total_rows // 100) == 0:
                self.progress_signal.emit(int((idx / total_rows) * 100))
                
            current_price = row['price']
            current_liq = row['liq']
            current_oi = row['oi_speed']
            current_time_str = row['time_str']
            
            # 실시간 세션별 매개변수 동적 결정 (설정창 기준 연동)
            if self.use_config_thresholds and self.session_thresholds:
                session_key = get_session_key(current_time_str)
                row_target_liq = self.session_thresholds.get(session_key, {}).get("liq", target_liq)
                row_target_oi = self.session_thresholds.get(session_key, {}).get("oi", target_oi)
                row_sl = abs(self.session_thresholds.get(session_key, {}).get("sl", -1.3)) / 100.0
            else:
                row_target_liq = target_liq
                row_target_oi = target_oi
                row_sl = stop_loss_pct
            
            # 시간 파싱 (쿨다운 연산용)
            try:
                current_ts = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S").timestamp()
            except Exception:
                current_ts = 0.0
            
            price_history.append(current_price)
            if len(price_history) > 60:
                price_history.pop(0)
                
            price_1m_ago = price_history[0] if price_history else current_price
            price_delta_1m = current_price - price_1m_ago
            
            if not is_in_position:
                # 쿨다운 제한 검사
                if current_ts < cooldown_until_ts:
                    continue
                # 동일 스파이크 중복 진입 방지 가드 (진입 간격 최소 60초)
                if current_ts - last_entry_ts < 60.0:
                    continue
                    
                # 진입 조건 검사 (세션 필터링 적용)
                session_key = get_session_key(current_time_str)
                if session_key in self.allowed_sessions:
                    if current_liq >= row_target_liq and abs(current_oi) >= row_target_oi:
                        is_in_position = True
                        has_second_entry = False
                        entry_price_1 = current_price
                        entry_price = current_price
                        entry_time = current_time_str
                        peak_pnl = 0.0
                        entry_liq = current_liq
                        entry_oi = current_oi
                        last_entry_ts = current_ts
                        
                        # 지능형 저격 방향성 판정 (본체와 정합화)
                        if price_delta_1m < 0 and current_oi < 0:
                            position_direction = "LONG"
                        elif price_delta_1m > 0 and current_oi < 0:
                            position_direction = "SHORT"
                        else:
                            position_direction = "LONG" if price_delta_1m > 0 else "SHORT"
            else:
                # 포지션 유지 중 ➡️ 2차 추가 매수 검사 또는 청산 조건 검사
                
                # 1차 진입가 기준 PnL 및 가중 평단 기준 PnL 계산
                if position_direction == "LONG":
                    pnl_from_entry_1 = (current_price - entry_price_1) / entry_price_1
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_from_entry_1 = (entry_price_1 - current_price) / entry_price_1
                    pnl_pct = (entry_price - current_price) / entry_price
                    
                peak_pnl = max(peak_pnl, pnl_pct)
                
                # 2차 추가 매수 조건 검사
                if not has_second_entry:
                    if pnl_from_entry_1 <= self.split_2_trigger_pct:
                        has_second_entry = True
                        entry_price_2 = current_price
                        # DCA 가중 평균 평단 갱신
                        entry_price = (entry_price_1 * self.split_1_ratio + entry_price_2 * self.split_2_ratio) / (self.split_1_ratio + self.split_2_ratio)
                        # 평단 변경에 따른 pnl_pct 재연산
                        if position_direction == "LONG":
                            pnl_pct = (current_price - entry_price) / entry_price
                        else:
                            pnl_pct = (entry_price - current_price) / entry_price
                        peak_pnl = 0.0 # 2차 추가 매집 즉시 고점 pnl 리셋
                        continue # 평단 변경 즉시 루프 다음으로 진행
                
                exit_triggered = False
                exit_reason = ""
                exit_pnl_pct = 0.0
                
                if has_second_entry:
                    # [2차 매집 완료 상태]: 1차 진입가 기준 최종 손절선만 연동 추종, 익절 락 배제
                    if pnl_from_entry_1 <= -row_sl:
                        exit_triggered = True
                        exit_reason = f"초기 손절선 (-{row_sl*100:.2f}% 도달, 1차 진입가 기준) [2차 매집]"
                        # 1차 진입가 기준 손절 도달 가격으로 강제 체결
                        if position_direction == "LONG":
                            sl_price = entry_price_1 * (1.0 - row_sl)
                            exit_pnl_pct = (sl_price - entry_price) / entry_price
                        else:
                            sl_price = entry_price_1 * (1.0 + row_sl)
                            exit_pnl_pct = (entry_price - sl_price) / entry_price
                            
                    # 반대 신호 감지
                    elif current_liq >= row_target_liq and abs(current_oi) >= row_target_oi:
                        if price_delta_1m < 0 and current_oi < 0:
                            new_dir = "LONG"
                        elif price_delta_1m > 0 and current_oi < 0:
                            new_dir = "SHORT"
                        else:
                            new_dir = "LONG" if price_delta_1m > 0 else "SHORT"
                            
                        if new_dir != position_direction:
                            exit_triggered = True
                            exit_reason = f"반대 방향 저격 신호 감지 (보유: {position_direction} / 신호: {new_dir}) [2차 매집]"
                            exit_pnl_pct = pnl_pct
                else:
                    # [1차 진입 상태]: 일반 1차 손절선 및 익절 락/추적 스탑 감시
                    # 1. 초기 손절선 검사
                    if pnl_pct <= -row_sl:
                        exit_triggered = True
                        exit_reason = f"초기 손절선 (-{row_sl*100:.2f}% 도달)"
                        exit_pnl_pct = -row_sl
                        
                    # 2. 익절 락 체크 (고점 돌파 후 되돌림 하락선 도달)
                    elif peak_pnl >= 0.015 and pnl_pct <= 0.010:
                        exit_triggered = True
                        exit_reason = "고점 +1.5% 돌파 후 하락선 +1.0% 도달 (익절 락)"
                        exit_pnl_pct = 0.010
                    elif peak_pnl >= 0.010 and pnl_pct <= 0.005:
                        exit_triggered = True
                        exit_reason = "고점 +1.0% 돌파 후 하락선 +0.5% 도달 (익절 락)"
                        exit_pnl_pct = 0.005
                    elif peak_pnl >= 0.006 and pnl_pct <= 0.002:
                        exit_triggered = True
                        exit_reason = "고점 +0.6% 돌파 후 하락선 +0.2% 도달 (익절 락)"
                        exit_pnl_pct = 0.002
                    # 3. 추적 스탑 (1.5% 이상 상승 후 고점 대비 1.0% 하락 시)
                    elif peak_pnl >= 0.015 and pnl_pct <= peak_pnl - 0.010:
                        exit_triggered = True
                        exit_reason = f"고점 {peak_pnl*100:.2f}% 돌파 후 1.0% 되돌림 도달 (추적 스탑)"
                        exit_pnl_pct = peak_pnl - 0.010
                    # 4. 반대 방향 저격 신호 감지 시 (최소 60초 의무 보유 시간 확보)
                    elif current_ts - last_entry_ts >= 60.0 and current_liq >= row_target_liq and abs(current_oi) >= row_target_oi:
                        # 신호 방향 판정
                        if price_delta_1m < 0 and current_oi < 0:
                            new_dir = "LONG"
                        elif price_delta_1m > 0 and current_oi < 0:
                            new_dir = "SHORT"
                        else:
                            new_dir = "LONG" if price_delta_1m > 0 else "SHORT"
                            
                        if new_dir != position_direction:
                            exit_triggered = True
                            exit_reason = f"반대 방향 저격 신호 감지 (보유: {position_direction} / 신호: {new_dir})"
                            exit_pnl_pct = pnl_pct
                        
                if exit_triggered:
                    is_in_position = False
                    cumulative_pnl += exit_pnl_pct * 100.0 # 누적 수익률 연산 (%)
                    equity_curve.append(cumulative_pnl)
                    
                    if position_direction == "LONG":
                        calc_exit_price = entry_price * (1.0 + exit_pnl_pct)
                    else:
                        calc_exit_price = entry_price * (1.0 - exit_pnl_pct)
                    
                    # 손절 청산 시 설정 시간, 익절/기타 청산 시 60초 쿨다운 적용 (동일 분 중복 진입 방지)
                    if "손절선" in exit_reason:
                        cooldown_until_ts = current_ts + self.cooldown_seconds
                    else:
                        cooldown_until_ts = current_ts + 60.0
                        
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time_str,
                        'direction': f"{position_direction} (1+2차)" if has_second_entry else f"{position_direction} (1차)",
                        'entry_price': entry_price,
                        'exit_price': calc_exit_price,
                        'reason': exit_reason,
                        'pnl_pct': exit_pnl_pct * 100.0,
                        'entry_session': get_session_name(get_session_key(entry_time)),
                        'entry_liq': entry_liq,
                        'entry_oi': entry_oi
                    })
                    
        self.progress_signal.emit(100)
        
        # 통계 계산
        total_trades = len(trades)
        win_trades = len([t for t in trades if t['pnl_pct'] > 0])
        loss_trades = total_trades - win_trades
        win_rate = (win_trades / total_trades * 100.0) if total_trades > 0 else 0.0
        
        # MDD 계산 (자산 곡선 기준)
        max_drawdown = 0.0
        peak_val = 0.0
        for val in equity_curve:
            peak_val = max(peak_val, val)
            drawdown = peak_val - val
            max_drawdown = max(max_drawdown, drawdown)
            
        result = {
            "success": True,
            "total_trades": total_trades,
            "win_trades": win_trades,
            "loss_trades": loss_trades,
            "win_rate": win_rate,
            "cumulative_pnl": cumulative_pnl,
            "mdd": max_drawdown,
            "trades": trades,
            "equity_curve": equity_curve
        }
        self.finished_signal.emit(result)

    def run_grid_optimization(self, all_data):
        liq_range = self.opt_ranges['liq']
        oi_range = self.opt_ranges['oi']
        sl_range = self.opt_ranges['sl']
        
        total_combinations = len(liq_range) * len(oi_range) * len(sl_range)
        comb_idx = 0
        
        results = []
        
        for liq in liq_range:
            for oi in oi_range:
                for sl in sl_range:
                    comb_idx += 1
                    self.progress_signal.emit(int((comb_idx / total_combinations) * 100))
                    
                    # 시뮬레이션
                    is_in_position = False
                    has_second_entry = False
                    position_direction = None
                    entry_price_1 = 0.0
                    entry_price_2 = 0.0
                    entry_price = 0.0
                    peak_pnl = 0.0
                    
                    trades_count = 0
                    win_count = 0
                    total_pnl = 0.0
                    
                    price_history = []
                    cooldown_until_ts = -999999.0
                    last_entry_ts = -999999.0
                    
                    for row in all_data:
                        current_price = row['price']
                        current_liq = row['liq']
                        current_oi = row['oi_speed']
                        current_time_str = row['time_str']
                        
                        try:
                            current_ts = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S").timestamp()
                        except Exception:
                            current_ts = 0.0
                        
                        price_history.append(current_price)
                        if len(price_history) > 60:
                            price_history.pop(0)
                        price_1m_ago = price_history[0] if price_history else current_price
                        price_delta_1m = current_price - price_1m_ago
                        
                        if not is_in_position:
                            if current_ts < cooldown_until_ts:
                                continue
                            if current_ts - last_entry_ts < 60.0:
                                continue
                                
                            session_key = get_session_key(current_time_str)
                            if session_key in self.allowed_sessions:
                                if current_liq >= liq and abs(current_oi) >= oi:
                                    is_in_position = True
                                    has_second_entry = False
                                    entry_price_1 = current_price
                                    entry_price = current_price
                                    peak_pnl = 0.0
                                    last_entry_ts = current_ts
                                    if price_delta_1m < 0 and current_oi < 0:
                                        position_direction = "LONG"
                                    elif price_delta_1m > 0 and current_oi < 0:
                                        position_direction = "SHORT"
                                    else:
                                        position_direction = "LONG" if price_delta_1m > 0 else "SHORT"
                        else:
                            if position_direction == "LONG":
                                pnl_from_entry_1 = (current_price - entry_price_1) / entry_price_1
                                pnl_pct = (current_price - entry_price) / entry_price
                            else:
                                pnl_from_entry_1 = (entry_price_1 - current_price) / entry_price_1
                                pnl_pct = (entry_price - current_price) / entry_price
                                
                            peak_pnl = max(peak_pnl, pnl_pct)
                            
                            if not has_second_entry:
                                if pnl_from_entry_1 <= self.split_2_trigger_pct:
                                    has_second_entry = True
                                    entry_price_2 = current_price
                                    entry_price = (entry_price_1 * self.split_1_ratio + entry_price_2 * self.split_2_ratio) / (self.split_1_ratio + self.split_2_ratio)
                                    if position_direction == "LONG":
                                        pnl_pct = (current_price - entry_price) / entry_price
                                    else:
                                        pnl_pct = (entry_price - current_price) / entry_price
                                    peak_pnl = 0.0
                                    continue
                            
                            exit_triggered = False
                            exit_pnl_pct = 0.0
                            
                            if has_second_entry:
                                if pnl_from_entry_1 <= -sl:
                                    exit_triggered = True
                                    if position_direction == "LONG":
                                        sl_price = entry_price_1 * (1.0 - sl)
                                        exit_pnl_pct = (sl_price - entry_price) / entry_price
                                    else:
                                        sl_price = entry_price_1 * (1.0 + sl)
                                        exit_pnl_pct = (entry_price - sl_price) / entry_price
                                elif current_ts - last_entry_ts >= 60.0 and current_liq >= liq and abs(current_oi) >= oi:
                                    if price_delta_1m < 0 and current_oi < 0:
                                        new_dir = "LONG"
                                    elif price_delta_1m > 0 and current_oi < 0:
                                        new_dir = "SHORT"
                                    else:
                                        new_dir = "LONG" if price_delta_1m > 0 else "SHORT"
                                    if new_dir != position_direction:
                                        exit_triggered = True
                                        exit_pnl_pct = pnl_pct
                            else:
                                if pnl_pct <= -sl:
                                    exit_triggered = True
                                    exit_pnl_pct = -sl
                                elif peak_pnl >= 0.015 and pnl_pct <= 0.010:
                                    exit_triggered = True
                                    exit_pnl_pct = 0.010
                                elif peak_pnl >= 0.010 and pnl_pct <= 0.005:
                                    exit_triggered = True
                                    exit_pnl_pct = 0.005
                                elif peak_pnl >= 0.006 and pnl_pct <= 0.002:
                                    exit_triggered = True
                                    exit_pnl_pct = 0.002
                                elif peak_pnl >= 0.015 and pnl_pct <= peak_pnl - 0.010:
                                    exit_triggered = True
                                    exit_pnl_pct = peak_pnl - 0.010
                                elif current_ts - last_entry_ts >= 60.0 and current_liq >= liq and abs(current_oi) >= oi:
                                    if price_delta_1m < 0 and current_oi < 0:
                                        new_dir = "LONG"
                                    elif price_delta_1m > 0 and current_oi < 0:
                                        new_dir = "SHORT"
                                    else:
                                        new_dir = "LONG" if price_delta_1m > 0 else "SHORT"
                                    if new_dir != position_direction:
                                        exit_triggered = True
                                        exit_pnl_pct = pnl_pct
                                        
                            if exit_triggered:
                                is_in_position = False
                                total_pnl += exit_pnl_pct * 100.0
                                trades_count += 1
                                if exit_pnl_pct > 0:
                                    win_count += 1
                                
                                # 손절 청산인 경우 설정 시간, 익절/기타 청산인 경우 즉시 진입 가능 (쿨다운 0초)
                                is_stop_loss_exit = False
                                if has_second_entry:
                                    if pnl_from_entry_1 <= -sl:
                                        is_stop_loss_exit = True
                                else:
                                    if pnl_pct <= -sl:
                                        is_stop_loss_exit = True
                                if is_stop_loss_exit:
                                    cooldown_until_ts = current_ts + self.cooldown_seconds
                                else:
                                    cooldown_until_ts = current_ts
                                    
                    win_rate = (win_count / trades_count * 100.0) if trades_count > 0 else 0.0
                    results.append({
                        'liq': liq,
                        'oi': oi,
                        'sl': sl,
                        'total_trades': trades_count,
                        'win_rate': win_rate,
                        'pnl': total_pnl
                    })
                    
        # 손익률 역정렬 후 상위 랭킹 결정
        results.sort(key=lambda x: x['pnl'], reverse=True)
        
        self.finished_signal.emit({
            "success": True,
            "grid_results": results
        })

# ==============================================================================
# 메인 윈도우 인터페이스 데시보드
# ==============================================================================
class ShinseonBacktester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("神選 [신선] 백테스터 & 파라미터 최적화 엔진 v1.0")
        self.resize(1100, 750)
        self.setStyleSheet(DARK_THEME_STYLE)
        
        self.config_data = {}
        self.load_config_data()
        
        # 메인 탭 위젯 생성
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.init_backtest_tab()
        self.init_optimizer_tab()
        
        self.scan_historical_files()
        
    def load_config_data(self):
        import json
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shinseon_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
        except Exception as e:
            print(f"Config load error: {e}")

    def init_backtest_tab(self):
        tab = QWidget()
        self.tabs.addTab(tab, "📊 단일 백테스팅 시뮬레이션")
        
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 좌측 제어용 스플리터
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # 파일 목록 그룹
        group_files = QGroupBox("1. 대상 데이터 파일 선택")
        files_vbox = QVBoxLayout(group_files)
        self.list_files = QListWidget()
        self.list_files.setSelectionMode(QListWidget.MultiSelection)
        self.list_files.setToolTip("백테스팅에 병합 반영할 오더플로우 데이터를 다중 선택하세요.")
        files_vbox.addWidget(self.list_files)
        
        self.btn_refresh_files = QPushButton("🔄 파일 검색 갱신")
        self.btn_refresh_files.clicked.connect(self.scan_historical_files)
        files_vbox.addWidget(self.btn_refresh_files)
        left_layout.addWidget(group_files)
        
        # 파라미터 입력 그룹
        group_params = QGroupBox("2. 진입/청산 매개변수")
        grid_params = QGridLayout(group_params)
        grid_params.setSpacing(10)
        
        self.lbl_edit_liq = QLabel("청산 임계치 ($):")
        grid_params.addWidget(self.lbl_edit_liq, 0, 0)
        self.edit_liq = QLineEdit("2500000")
        self.edit_liq.setPlaceholderText("예: 2500000")
        grid_params.addWidget(self.edit_liq, 0, 1)
        
        self.lbl_edit_oi = QLabel("OI 속도 임계치 (%):")
        grid_params.addWidget(self.lbl_edit_oi, 1, 0)
        self.edit_oi = QLineEdit("0.12")
        self.edit_oi.setPlaceholderText("예: 0.12")
        grid_params.addWidget(self.edit_oi, 1, 1)
        
        self.lbl_edit_sl = QLabel("초기 손절선 (SL, %):")
        grid_params.addWidget(self.lbl_edit_sl, 2, 0)
        self.edit_sl = QLineEdit("1.3")
        self.edit_sl.setPlaceholderText("예: 1.3")
        grid_params.addWidget(self.edit_sl, 2, 1)
        
        # 세션 선택 체크박스 (개발계획서_188_17)
        grid_params.addWidget(QLabel("대상 세션 필터:"), 3, 0)
        
        sess_layout = QHBoxLayout()
        self.chk_back_asia = QCheckBox("🔴 아시아")
        self.chk_back_asia.setChecked(True)
        self.chk_back_europe = QCheckBox("🟡 유럽")
        self.chk_back_europe.setChecked(True)
        self.chk_back_us = QCheckBox("🟢 미국")
        self.chk_back_us.setChecked(True)
        self.chk_back_pacific = QCheckBox("⚪ 태평양")
        self.chk_back_pacific.setChecked(True)
        
        sess_layout.addWidget(self.chk_back_asia)
        sess_layout.addWidget(self.chk_back_europe)
        sess_layout.addWidget(self.chk_back_us)
        sess_layout.addWidget(self.chk_back_pacific)
        
        grid_params.addLayout(sess_layout, 4, 0, 1, 2)
        
        # 세션별 설정값 자동 적용 체크박스 추가
        self.chk_use_config_thresholds = QCheckBox("⚙️ 세션별 설정값 자동 적용 (설정창 기준)")
        self.chk_use_config_thresholds.setChecked(True) # Checked by default!
        self.chk_use_config_thresholds.stateChanged.connect(self.toggle_param_inputs)
        grid_params.addWidget(self.chk_use_config_thresholds, 5, 0, 1, 2)
        
        # 세션별 설정값 상세 편집 버튼 추가
        self.btn_edit_session_config = QPushButton("⚙️ 세션별 설정값 상세 편집")
        self.btn_edit_session_config.clicked.connect(self.open_session_config_editor)
        grid_params.addWidget(self.btn_edit_session_config, 6, 0, 1, 2)
        
        # 기본적으로 체크 상태이므로 매개변수 에디터 숨김 트리거
        self.lbl_edit_liq.setVisible(False)
        self.edit_liq.setVisible(False)
        self.lbl_edit_oi.setVisible(False)
        self.edit_oi.setVisible(False)
        self.lbl_edit_sl.setVisible(False)
        self.edit_sl.setVisible(False)
        
        left_layout.addWidget(group_params)
        
        # 3. 분할 매수 및 쿨다운 설정 그룹 (개발계획서_188_19)
        group_split = QGroupBox("3. 분할 매수 및 쿨다운 설정")
        grid_split = QGridLayout(group_split)
        grid_split.setSpacing(10)
        
        cfg = self.config_data
        
        grid_split.addWidget(QLabel("1차 매수 비중 (%):"), 0, 0)
        self.edit_split_1 = QLineEdit(str(cfg.get("split_entry_1_ratio", 250.0)))
        self.edit_split_1.setPlaceholderText("예: 250.0")
        grid_split.addWidget(self.edit_split_1, 0, 1)
        
        grid_split.addWidget(QLabel("2차 매수 비중 (%):"), 1, 0)
        self.edit_split_2 = QLineEdit(str(cfg.get("split_entry_2_ratio", 200.0)))
        self.edit_split_2.setPlaceholderText("예: 200.0")
        grid_split.addWidget(self.edit_split_2, 1, 1)
        
        grid_split.addWidget(QLabel("2차 진입 하락폭 (%):"), 2, 0)
        self.edit_split_trigger = QLineEdit(str(cfg.get("split_entry_2_trigger_pct", -0.50)))
        self.edit_split_trigger.setPlaceholderText("예: -0.50")
        grid_split.addWidget(self.edit_split_trigger, 2, 1)
        
        grid_split.addWidget(QLabel("손절 후 제한시간 (초):"), 3, 0)
        self.edit_cooldown = QLineEdit(str(cfg.get("cooldown_seconds", 300.0)))
        self.edit_cooldown.setPlaceholderText("예: 300.0")
        grid_split.addWidget(self.edit_cooldown, 3, 1)
        
        grid_split.addWidget(QLabel("포지션 레버리지 배수 (배):"), 4, 0)
        self.edit_leverage = QLineEdit(str(cfg.get("leverage_level", 20)))
        self.edit_leverage.setPlaceholderText("예: 20")
        grid_split.addWidget(self.edit_leverage, 4, 1)
        
        left_layout.addWidget(group_split)

        # 백테스팅 가동 버튼
        self.btn_run_backtest = QPushButton("🚀 백테스팅 실행 (시뮬레이션 개시)")
        self.btn_run_backtest.setFixedHeight(40)
        self.btn_run_backtest.clicked.connect(self.start_backtest)
        left_layout.addWidget(self.btn_run_backtest)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(15)
        left_layout.addWidget(self.progress_bar)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(320)
        layout.addWidget(left_widget)
        
        # 우측 결과 패널
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        
        # 카드식 성적 보고 보드
        board_layout = QHBoxLayout()
        
        self.card_pnl = QGroupBox("총 누적 손익률")
        pnl_vbox = QVBoxLayout(self.card_pnl)
        self.val_pnl = QLabel("0.00%")
        self.val_pnl.setStyleSheet("font-size: 24px; font-weight: bold; color: #DEBA9D;")
        self.val_pnl.setAlignment(Qt.AlignCenter)
        pnl_vbox.addWidget(self.val_pnl)
        
        self.card_winrate = QGroupBox("저격 승률")
        win_vbox = QVBoxLayout(self.card_winrate)
        self.val_winrate = QLabel("0.0%")
        self.val_winrate.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        self.val_winrate.setAlignment(Qt.AlignCenter)
        win_vbox.addWidget(self.val_winrate)
        
        self.card_trades = QGroupBox("총 거래 횟수")
        trades_vbox = QVBoxLayout(self.card_trades)
        self.val_trades = QLabel("0회")
        self.val_trades.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        self.val_trades.setAlignment(Qt.AlignCenter)
        trades_vbox.addWidget(self.val_trades)
        
        self.card_mdd = QGroupBox("최대 낙폭 (MDD)")
        mdd_vbox = QVBoxLayout(self.card_mdd)
        self.val_mdd = QLabel("0.00%")
        self.val_mdd.setStyleSheet("font-size: 24px; font-weight: bold; color: #CF6679;")
        self.val_mdd.setAlignment(Qt.AlignCenter)
        mdd_vbox.addWidget(self.val_mdd)
        
        board_layout.addWidget(self.card_pnl)
        board_layout.addWidget(self.card_winrate)
        board_layout.addWidget(self.card_trades)
        board_layout.addWidget(self.card_mdd)
        right_layout.addLayout(board_layout)
        
        # 에쿼티 커브
        self.chart_equity = EquityChartWidget()
        right_layout.addWidget(self.chart_equity)
        
        # 상세 거래 테이블
        self.table_trades = QTableWidget()
        self.table_trades.setColumnCount(10)
        self.table_trades.setHorizontalHeaderLabels([
            "진입 시간", "진입 세션", "방향", "진입 가격", "진입 청산액", "진입 OI속도", "청산 시간", "청산 가격", "손익률", "청산 사유"
        ])
        self.table_trades.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_trades.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        right_layout.addWidget(self.table_trades)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        layout.addWidget(right_widget)

    def init_optimizer_tab(self):
        tab = QWidget()
        self.tabs.addTab(tab, "⚡ 그리드 최적 파라미터 검색기")
        
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 좌측
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        group_files_opt = QGroupBox("1. 대상 데이터 파일 선택")
        files_vbox_opt = QVBoxLayout(group_files_opt)
        self.list_files_opt = QListWidget()
        self.list_files_opt.setSelectionMode(QListWidget.MultiSelection)
        files_vbox_opt.addWidget(self.list_files_opt)
        
        self.btn_refresh_files_opt = QPushButton("🔄 파일 목록 갱신")
        self.btn_refresh_files_opt.clicked.connect(self.scan_historical_files)
        files_vbox_opt.addWidget(self.btn_refresh_files_opt)
        left_layout.addWidget(group_files_opt)
        
        # 검색 범위 설정
        group_ranges = QGroupBox("2. 최적화 대입 후보군 범위")
        grid_ranges = QGridLayout(group_ranges)
        grid_ranges.setSpacing(10)
        
        grid_ranges.addWidget(QLabel("청산 임계치 범위 ($):"), 0, 0)
        self.edit_opt_liq = QLineEdit("1000000, 1500000, 2000000, 2500000, 3000000")
        grid_ranges.addWidget(self.edit_opt_liq, 0, 1)
        
        grid_ranges.addWidget(QLabel("OI 가속도 범위 (%):"), 1, 0)
        self.edit_opt_oi = QLineEdit("0.08, 0.10, 0.12, 0.14, 0.16")
        grid_ranges.addWidget(self.edit_opt_oi, 1, 1)
        
        grid_ranges.addWidget(QLabel("손절폭(SL) 범위 (%):"), 2, 0)
        self.edit_opt_sl = QLineEdit("1.0, 1.3, 1.5")
        grid_ranges.addWidget(self.edit_opt_sl, 2, 1)
        
        # 세션 선택 체크박스 (개발계획서_188_17)
        grid_ranges.addWidget(QLabel("대상 세션 필터:"), 3, 0)
        
        sess_opt_layout = QHBoxLayout()
        self.chk_opt_asia = QCheckBox("🔴 아시아")
        self.chk_opt_asia.setChecked(True)
        self.chk_opt_europe = QCheckBox("🟡 유럽")
        self.chk_opt_europe.setChecked(True)
        self.chk_opt_us = QCheckBox("🟢 미국")
        self.chk_opt_us.setChecked(True)
        self.chk_opt_pacific = QCheckBox("⚪ 태평양")
        self.chk_opt_pacific.setChecked(True)
        
        sess_opt_layout.addWidget(self.chk_opt_asia)
        sess_opt_layout.addWidget(self.chk_opt_europe)
        sess_opt_layout.addWidget(self.chk_opt_us)
        sess_opt_layout.addWidget(self.chk_opt_pacific)
        
        grid_ranges.addLayout(sess_opt_layout, 4, 0, 1, 2)
        
        left_layout.addWidget(group_ranges)
        
        self.btn_run_optimizer = QPushButton("⚡ 그리드 최적화 가동 (Grid Search)")
        self.btn_run_optimizer.setFixedHeight(40)
        self.btn_run_optimizer.clicked.connect(self.start_optimizer)
        left_layout.addWidget(self.btn_run_optimizer)
        
        self.progress_bar_opt = QProgressBar()
        self.progress_bar_opt.setValue(0)
        self.progress_bar_opt.setFixedHeight(15)
        left_layout.addWidget(self.progress_bar_opt)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(320)
        layout.addWidget(left_widget)
        
        # 우측 최적화 결과
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        right_layout.addWidget(QLabel("📊 [최적 파라미터 조합 랭킹 결과]"))
        
        self.table_opt_results = QTableWidget()
        self.table_opt_results.setColumnCount(7)
        self.table_opt_results.setHorizontalHeaderLabels([
            "순위", "청산 임계치 ($)", "OI 속도 (% )", "손절선 (%)", "가상 진입 수", "저격 승률", "총 누적 수익률"
        ])
        self.table_opt_results.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_layout.addWidget(self.table_opt_results)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        layout.addWidget(right_widget)

    def open_session_config_editor(self):
        import json
        self.load_config_data()
        session_thresholds = self.config_data.get("session_thresholds", {
            "asia": {"liq": 400000.0, "oi": 0.09, "sl": -1.3},
            "europe": {"liq": 600000.0, "oi": 0.10, "sl": -1.0},
            "us": {"liq": 400000.0, "oi": 0.15, "sl": -1.3},
            "pacific": {"liq": 400000.0, "oi": 0.07, "sl": -1.0}
        })
        
        dialog = SessionConfigEditDialog(session_thresholds, self)
        if dialog.exec() == QDialog.Accepted:
            new_thresholds = {}
            for s_key, fields in dialog.fields.items():
                try:
                    liq = float(fields["liq"].text().replace(",", "").strip())
                    oi = float(fields["oi"].text().strip())
                    sl = float(fields["sl"].text().strip())
                    new_thresholds[s_key] = {"liq": liq, "oi": oi, "sl": sl}
                except ValueError:
                    QMessageBox.warning(self, "알림", "올바르지 않은 숫자 형식이 존재하여 저장에 실패했습니다.")
                    return
            
            self.config_data["session_thresholds"] = new_thresholds
            
            try:
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shinseon_config.json")
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "완료", "세션별 설정값이 성공적으로 적용 및 저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "에러", f"설정 파일 저장 중 에러 발생: {e}")

    def toggle_param_inputs(self, state):
        from qtpy.QtCore import Qt
        visible = (state != Qt.Checked)
        
        self.lbl_edit_liq.setVisible(visible)
        self.edit_liq.setVisible(visible)
        
        self.lbl_edit_oi.setVisible(visible)
        self.edit_oi.setVisible(visible)
        
        self.lbl_edit_sl.setVisible(visible)
        self.edit_sl.setVisible(visible)

    def scan_historical_files(self):
        # 파일 스캔하여 리스트 위젯에 수록
        self.list_files.clear()
        self.list_files_opt.clear()
        
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            
        files = [f for f in os.listdir(DATA_DIR) if f.startswith("orderflow_history_") and f.endswith(".csv")]
        files.sort(reverse=True)
        
        if not files:
            QMessageBox.warning(self, "알림", f"docs/historical_data/ 폴더에 orderflow_history_*.csv 형태의 누적 시세 데이터 파일이 하나도 존재하지 않습니다.\n봇을 켜두어 시세 데이터가 기록된 후에 활용 가능합니다.")
            return
            
        for f in files:
            # 단일 백테스트 리스트 추가
            item = QListWidgetItem(f)
            self.list_files.addItem(item)
            
            # 최적화 리스트 추가
            item_opt = QListWidgetItem(f)
            self.list_files_opt.addItem(item_opt)
            
        # 첫 번째 항목 자동 선택
        if self.list_files.count() > 0:
            self.list_files.item(0).setSelected(True)
            self.list_files_opt.item(0).setSelected(True)

    def start_backtest(self):
        selected_items = self.list_files.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "알림", "백테스팅에 대입할 시세 데이터 파일을 한 개 이상 선택해 주십시오.")
            return
            
        selected_paths = [os.path.join(DATA_DIR, item.text()) for item in selected_items]
        
        use_cfg = self.chk_use_config_thresholds.isChecked()
        try:
            liq = 0.0 if use_cfg else float(self.edit_liq.text().replace(",", ""))
            oi = 0.0 if use_cfg else float(self.edit_oi.text())
            sl = 0.0 if use_cfg else abs(float(self.edit_sl.text())) / 100.0
        except ValueError:
            if not use_cfg:
                QMessageBox.critical(self, "에러", "진입/청산 매개변수에 올바른 숫자 값을 입력해 주십시오.")
                return
            else:
                liq, oi, sl = 0.0, 0.0, 0.0
            
        # 세션 선택 값 파싱
        allowed_sessions = []
        if self.chk_back_asia.isChecked(): allowed_sessions.append("asia")
        if self.chk_back_europe.isChecked(): allowed_sessions.append("europe")
        if self.chk_back_us.isChecked(): allowed_sessions.append("us")
        if self.chk_back_pacific.isChecked(): allowed_sessions.append("pacific")
        
        if not allowed_sessions:
            QMessageBox.warning(self, "알림", "테스트할 세션을 최소한 하나 이상 선택해 주십시오.")
            return

        self.btn_run_backtest.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # DCA, 레버리지 및 쿨다운 값 파싱
        try:
            split_1 = float(self.edit_split_1.text().strip())
            split_2 = float(self.edit_split_2.text().strip())
            split_trigger = float(self.edit_split_trigger.text().strip()) / 100.0
            cooldown = float(self.edit_cooldown.text().strip())
            leverage = int(float(self.edit_leverage.text().strip()))
        except ValueError:
            QMessageBox.critical(self, "에러", "분할 매수, 레버리지 및 쿨다운 매개변수에 올바른 숫자 값을 입력해 주십시오.")
            return

        # 설정 동기화 저장
        self.config_data["split_entry_1_ratio"] = split_1
        self.config_data["split_entry_2_ratio"] = split_2
        self.config_data["split_entry_2_trigger_pct"] = float(self.edit_split_trigger.text().strip())
        self.config_data["cooldown_seconds"] = cooldown
        self.config_data["leverage_level"] = leverage
        
        try:
            import json
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shinseon_config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config on backtest: {e}")

        self.worker = BacktestWorker(
            selected_paths, liq, oi, sl, is_optimizer=False, allowed_sessions=allowed_sessions,
            split_1_ratio=split_1, split_2_ratio=split_2, split_2_trigger_pct=split_trigger, cooldown_seconds=cooldown,
            use_config_thresholds=use_cfg, session_thresholds=self.config_data.get("session_thresholds", None)
        )
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_backtest_finished)
        self.worker.start()

    def on_backtest_finished(self, results):
        self.btn_run_backtest.setEnabled(True)
        if not results.get("success", False):
            QMessageBox.critical(self, "에러", results.get("error", "알 수 없는 에러가 발생했습니다."))
            return
            
        # UI 업데이트
        pnl = results["cumulative_pnl"]
        win_rate = results["win_rate"]
        trades_count = results["total_trades"]
        mdd = results["mdd"]
        
        self.val_pnl.setText(f"{pnl:+.2f}%")
        if pnl > 0:
            self.val_pnl.setStyleSheet("font-size: 24px; font-weight: bold; color: #6200EE; color: #DEBA9D;")
        else:
            self.val_pnl.setStyleSheet("font-size: 24px; font-weight: bold; color: #CF6679;")
            
        self.val_winrate.setText(f"{win_rate:.1f}%")
        self.val_trades.setText(f"{trades_count}회")
        self.val_mdd.setText(f"{mdd:.2f}%")
        
        # 에쿼티 차트 바인딩
        self.chart_equity.set_data(results["equity_curve"])
        
        # 상세 테이블 리셋 및 적재
        self.table_trades.setRowCount(0)
        for row_idx, trade in enumerate(results["trades"]):
            self.table_trades.insertRow(row_idx)
            
            pnl_val = trade['pnl_pct']
            pnl_item = QTableWidgetItem(f"{pnl_val:+.2f}%")
            if pnl_val > 0:
                pnl_item.setForeground(QColor("#DEBA9D"))
            else:
                pnl_item.setForeground(QColor("#CF6679"))
                
            self.table_trades.setItem(row_idx, 0, QTableWidgetItem(trade['entry_time']))
            self.table_trades.setItem(row_idx, 1, QTableWidgetItem(trade.get('entry_session', '알 수 없음')))
            self.table_trades.setItem(row_idx, 2, QTableWidgetItem(trade['direction']))
            self.table_trades.setItem(row_idx, 3, QTableWidgetItem(f"${trade['entry_price']:,.1f}"))
            
            # 신규 진입 임계치 컬럼 세팅 (개발계획서_188_20)
            liq_val = trade.get('entry_liq', 0.0)
            oi_val = trade.get('entry_oi', 0.0)
            self.table_trades.setItem(row_idx, 4, QTableWidgetItem(f"${liq_val:,.0f}"))
            self.table_trades.setItem(row_idx, 5, QTableWidgetItem(f"{oi_val:+.4f}%"))
            
            self.table_trades.setItem(row_idx, 6, QTableWidgetItem(trade['exit_time']))
            self.table_trades.setItem(row_idx, 7, QTableWidgetItem(f"${trade['exit_price']:,.1f}"))
            self.table_trades.setItem(row_idx, 8, pnl_item)
            self.table_trades.setItem(row_idx, 9, QTableWidgetItem(trade['reason']))

    def start_optimizer(self):
        selected_items = self.list_files_opt.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "알림", "최적화에 대입할 시세 데이터 파일을 한 개 이상 선택해 주십시오.")
            return
            
        selected_paths = [os.path.join(DATA_DIR, item.text()) for item in selected_items]
        
        # 범위 해석
        try:
            liq_vals = [float(x.strip()) for x in self.edit_opt_liq.text().split(",")]
            oi_vals = [float(x.strip()) for x in self.edit_opt_oi.text().split(",")]
            sl_vals = [abs(float(x.strip())) / 100.0 for x in self.edit_opt_sl.text().split(",")] # abs 적용
        except ValueError:
            QMessageBox.critical(self, "에러", "최적화 후보 범위에 쉼표(,)로 구분된 올바른 숫자들을 입력해 주십시오.")
            return
            
        # 세션 선택 값 파싱
        allowed_sessions = []
        if self.chk_opt_asia.isChecked(): allowed_sessions.append("asia")
        if self.chk_opt_europe.isChecked(): allowed_sessions.append("europe")
        if self.chk_opt_us.isChecked(): allowed_sessions.append("us")
        if self.chk_opt_pacific.isChecked(): allowed_sessions.append("pacific")
        
        if not allowed_sessions:
            QMessageBox.warning(self, "알림", "최적화할 세션을 최소한 하나 이상 선택해 주십시오.")
            return

        self.btn_run_optimizer.setEnabled(False)
        self.progress_bar_opt.setValue(0)
        
        opt_ranges = {'liq': liq_vals, 'oi': oi_vals, 'sl': sl_vals}
        
        # DCA 및 쿨다운 값 파싱
        try:
            split_1 = float(self.edit_split_1.text().strip())
            split_2 = float(self.edit_split_2.text().strip())
            split_trigger = float(self.edit_split_trigger.text().strip()) / 100.0
            cooldown = float(self.edit_cooldown.text().strip())
        except ValueError:
            split_1 = 250.0
            split_2 = 200.0
            split_trigger = -0.005
            cooldown = 300.0

        self.worker = BacktestWorker(
            selected_paths, 0, 0, 0, is_optimizer=True, opt_ranges=opt_ranges, allowed_sessions=allowed_sessions,
            split_1_ratio=split_1, split_2_ratio=split_2, split_2_trigger_pct=split_trigger, cooldown_seconds=cooldown
        )
        self.worker.progress_signal.connect(self.progress_bar_opt.setValue)
        self.worker.finished_signal.connect(self.on_optimizer_finished)
        self.worker.start()

    def on_optimizer_finished(self, results):
        self.btn_run_optimizer.setEnabled(True)
        if not results.get("success", False):
            QMessageBox.critical(self, "에러", results.get("error", "알 수 없는 에러가 발생했습니다."))
            return
            
        # 테이블 바인딩
        self.table_opt_results.setRowCount(0)
        
        for row_idx, res in enumerate(results["grid_results"]):
            if row_idx >= 50: # 상위 50개만 표출
                break
                
            self.table_opt_results.insertRow(row_idx)
            
            pnl_val = res['pnl']
            pnl_item = QTableWidgetItem(f"{pnl_val:+.2f}%")
            if pnl_val > 0:
                pnl_item.setForeground(QColor("#DEBA9D"))
            else:
                pnl_item.setForeground(QColor("#CF6679"))
                
            self.table_opt_results.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            self.table_opt_results.setItem(row_idx, 1, QTableWidgetItem(f"${int(res['liq']):,}"))
            self.table_opt_results.setItem(row_idx, 2, QTableWidgetItem(f"{res['oi']:.2f}%"))
            self.table_opt_results.setItem(row_idx, 3, QTableWidgetItem(f"{res['sl']*100:.1f}%"))
            self.table_opt_results.setItem(row_idx, 4, QTableWidgetItem(f"{res['total_trades']}회"))
            self.table_opt_results.setItem(row_idx, 5, QTableWidgetItem(f"{res['win_rate']:.1f}%"))
            self.table_opt_results.setItem(row_idx, 6, pnl_item)

# ==============================================================================
# 메인 런처
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 아크 테마 색상 강제 지정
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#121212"))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor("#161514"))
    palette.setColor(QPalette.AlternateBase, QColor("#1A1816"))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor("#242220"))
    palette.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(palette)
    
    window = ShinseonBacktester()
    window.show()
    sys.exit(app.exec())
