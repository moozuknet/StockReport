import os
import sys
from pathlib import Path
from datetime import datetime, date
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGroupBox, QCheckBox, QRadioButton, QLineEdit, QComboBox,
    QPushButton, QLabel, QFileDialog, QTextEdit, QMessageBox,
    QFrame, QGridLayout, QDateEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QTextCursor, QTextBlockFormat, QIcon

from config import AppConfig, SITE_KEYS, send_telegram_message
from scheduler import ReportScheduler
from collectors import CollectorManager

def get_resource_path(relative_path: str) -> str:
    """PyInstaller 묶음 파일(sys._MEIPASS) 및 소스 경로에서 리소스 경로를 탐색합니다."""
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(p):
            return p
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p1 = os.path.join(base_dir, relative_path)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(os.getcwd(), relative_path)
    if os.path.exists(p2):
        return p2
    return relative_path

class PyQtLogPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("실행 로그", parent)
        self.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #263238;
                border: 1px solid #CFD8DC;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 14px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                padding: 0 6px;
                background-color: #FFFFFF;
            }
        """)
        self.success_count = 0
        self.skip_count = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        top_bar = QHBoxLayout()
        self.status_lbl = QLabel("상태: 대기 중 ⏱️")
        self.status_lbl.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.status_lbl.setStyleSheet("color: #0288D1;")
        top_bar.addWidget(self.status_lbl)
        
        top_bar.addStretch()
        
        clear_btn = QPushButton("🧹 로그 지우기")
        clear_btn.setFont(QFont("맑은 고딕", 9))
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F7FA;
                color: #455A64;
                border: 1px solid #CFD8DC;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ECEFF1;
                color: #263238;
            }
        """)
        clear_btn.clicked.connect(self.clear_logs)
        top_bar.addWidget(clear_btn)
        
        layout.addLayout(top_bar)
        
        # 하얀 카드 테두리 속 딥 다크 콘솔 박스
        card_frame = QFrame()
        card_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #ECEFF1;
                border-radius: 6px;
            }
        """)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(4, 4, 4, 4)
        
        # 로그창 높이를 280px 이상으로 높이고 여러 줄이 수직 확장되어 보이도록 구현
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("맑은 고딕", 10))
        self.log_area.setMinimumHeight(280)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 6px;
                selection-background-color: #264F78;
                selection-color: #FFFFFF;
            }
            QScrollBar:vertical {
                border: none;
                background: #1E1E1E;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        card_layout.addWidget(self.log_area)
        layout.addWidget(card_frame)

    def log(self, message: str):
        # 1. 새 수집 회차가 시작되면 카운터 초기화
        if "통합 증권 리포트 수집 시작" in message or "수집 스케줄러가 시작되었습니다" in message:
            self.success_count = 0
            self.skip_count = 0

        # 2. 신규 PDF 파일 다운로드 성공 시에만 카운트 (증권사 수집 완료 헤더 제외)
        if "[성공]" in message and "완료" not in message:
            self.success_count += 1

        # 3. 실제 PDF 중복/유사 스킵 시에만 카운트 (저장 경로 알림 라인 제외)
        if "[스킵]" in message or "[유사 스킵" in message:
            self.skip_count += 1

        timestamp = datetime.now().strftime("%H:%M:%S - ")
        full_text = f"{timestamp} {message}"

        # 120% 비율의 적당하고 정갈한 행간(Line Height) 설정
        cursor = self.log_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        block_fmt = QTextBlockFormat()
        block_fmt.setLineHeight(120, QTextBlockFormat.ProportionalHeight)
        cursor.insertBlock(block_fmt)
        cursor.insertText(full_text)
        
        self.log_area.setTextCursor(cursor)
        self.log_area.ensureCursorVisible()
        
        self.status_lbl.setText(f"✅ 신규 다운로드: {self.success_count}개 | 📁 중복 스킵: {self.skip_count}개")

    def clear_logs(self):
        self.log_area.clear()
        self.success_count = 0
        self.skip_count = 0
        self.status_lbl.setText("상태: 로그 초기화됨 🧹")

class StockReportQtApp(QMainWindow):
    log_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = AppConfig.load_from_json()
        self.collector_manager = CollectorManager()
        
        self.finish_signal.connect(self._on_schedule_finished)
        self.scheduler = ReportScheduler(
            self.config, 
            self._emit_log, 
            runner_fn=self.collector_manager.run,
            on_finished=self.finish_signal.emit
        )
        
        self.setWindowTitle("증권사별 리포트 자동 수집기")
        icon_file = get_resource_path("app_icon.png")
        if not os.path.exists(icon_file):
            icon_file = get_resource_path("app_icon.ico")
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))
        self.resize(920, 960)
        
        self._is_loading_config = True
        self._apply_global_style()
        self._build_ui()
        self._load_config_to_ui()
        self._connect_ui_signals()
        self._is_loading_config = False
        
        self.log_signal.connect(self.log_panel.log)
        self._bring_to_front()

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F4F6F8;
            }
            QWidget {
                color: #37474F;
            }
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #263238;
                border: 1px solid #CFD8DC;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                padding: 0 6px;
                background-color: #FFFFFF;
            }
            QLineEdit, QDateEdit, QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #B0BEC5;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 2px solid #0288D1;
            }
            QCheckBox {
                font-size: 13px;
                padding: 5px 10px;
                background-color: #F8F9FA;
                border: 1px solid #ECEFF1;
                border-radius: 6px;
            }
            QCheckBox:hover {
                background-color: #ECEFF1;
                border-color: #B0BEC5;
            }
            QRadioButton {
                font-size: 13px;
                spacing: 6px;
            }
        """)

    def _emit_log(self, msg: str):
        self.log_signal.emit(msg)

    def _on_schedule_finished(self):
        """수집 완료(또는 1회성 종료) 시 UI 버튼 상태를 자동 복원합니다."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_panel.status_lbl.setText(f"✅ 신규 다운로드: {self.log_panel.success_count}개 | 📁 중복 스킵: {self.log_panel.skip_count}개 (작업 완료됨)")

    def _bring_to_front(self):
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. 헤더 타이틀
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1A237E, stop:1 #0288D1);
                border-radius: 8px;
            }
        """)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 10, 16, 10)
        
        header_lbl = QLabel("📊 증권사별 리포트 자동 수집기")
        header_lbl.setFont(QFont("맑은 고딕", 13, QFont.Bold))
        header_lbl.setStyleSheet("color: #FFFFFF;")
        header_lbl.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_lbl)
        main_layout.addWidget(header_card)

        # 2. 실행 기능 선택 그룹 (체크박스로 기능 분리 선택)
        feature_group = QGroupBox("🎯 실행 기능 선택 (원하는 작업 체크)")
        feature_layout = QHBoxLayout(feature_group)
        feature_layout.setContentsMargins(14, 14, 14, 14)
        feature_layout.setSpacing(20)

        self.enable_download_cb = QCheckBox("📥 증권사 리포트 다운로드 수집")
        self.enable_download_cb.setCursor(Qt.PointingHandCursor)
        self.enable_download_cb.setChecked(True)

        self.enable_ai_summary_cb = QCheckBox("🤖 AI 리포트 분석 및 요약")
        self.enable_ai_summary_cb.setCursor(Qt.PointingHandCursor)
        self.enable_ai_summary_cb.setChecked(True)

        feature_layout.addWidget(self.enable_download_cb)
        feature_layout.addWidget(self.enable_ai_summary_cb)
        feature_layout.addStretch()
        main_layout.addWidget(feature_group)

        # 3. 사이트 선택 그룹
        site_group = QGroupBox("수집 대상 사이트 선택")
        site_layout = QVBoxLayout(site_group)
        site_layout.setContentsMargins(14, 14, 14, 14)
        site_layout.setSpacing(10)
        
        btn_box = QHBoxLayout()
        select_all_btn = QPushButton("전체 선택")
        deselect_all_btn = QPushButton("전체 해제")
        for btn in [select_all_btn, deselect_all_btn]:
            btn.setFont(QFont("맑은 고딕", 9, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedWidth(90)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #E3F2FD;
                    color: #0277BD;
                    border: 1px solid #90CAF9;
                    border-radius: 6px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #BBDEFB;
                }
            """)
        select_all_btn.clicked.connect(self._select_all_sites)
        deselect_all_btn.clicked.connect(self._deselect_all_sites)
        btn_box.addWidget(select_all_btn)
        btn_box.addWidget(deselect_all_btn)
        btn_box.addStretch()
        site_layout.addLayout(btn_box)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        
        self.site_checkboxes = {}
        for idx, site_key in enumerate(SITE_KEYS):
            cb = QCheckBox(site_key)
            cb.setCursor(Qt.PointingHandCursor)
            cb.setChecked(True)
            self.site_checkboxes[site_key] = cb
            grid.addWidget(cb, idx // 4, idx % 4)

        site_layout.addLayout(grid)
        main_layout.addWidget(site_group)

        # 4. 저장 경로, 날짜, AI 키 & 스케줄 동작 주기 설정 그룹
        settings_group = QGroupBox("저장 경로, 날짜, AI & 텔레그램 설정")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(14, 14, 14, 14)
        settings_layout.setSpacing(10)

        # 저장 폴더
        dir_layout = QHBoxLayout()
        dir_lbl = QLabel("저장 폴더:")
        dir_lbl.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.save_dir_edit = QLineEdit()
        
        browse_btn = QPushButton("📁 폴더 찾아보기")
        browse_btn.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #ECEFF1;
                color: #37474F;
                border: 1px solid #B0BEC5;
                border-radius: 6px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #CFD8DC;
            }
        """)
        browse_btn.clicked.connect(self._browse_save_dir)

        dir_layout.addWidget(dir_lbl)
        dir_layout.addWidget(self.save_dir_edit)
        dir_layout.addWidget(browse_btn)
        settings_layout.addLayout(dir_layout)

        self.auto_subfolder_cb = QCheckBox("날짜별 하위 폴더 자동 생성 (예: Downloads/20260729)")
        self.auto_subfolder_cb.setCursor(Qt.PointingHandCursor)
        settings_layout.addWidget(self.auto_subfolder_cb)

        # Gemini API Key 설정
        gemini_layout = QHBoxLayout()
        gemini_lbl = QLabel("🤖 Gemini API Key:")
        gemini_lbl.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setPlaceholderText("Google Gemini API Key 입력 (미입력 시 자체 요약 모드로 작동)")
        self.gemini_key_edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        gemini_layout.addWidget(gemini_lbl)
        gemini_layout.addWidget(self.gemini_key_edit)
        settings_layout.addLayout(gemini_layout)

        # 동작 주기 (스케줄러 주기) 설정
        interval_layout = QHBoxLayout()
        interval_lbl = QLabel("⏱️ 동작 주기 설정:")
        interval_lbl.setFont(QFont("맑은 고딕", 9, QFont.Bold))

        self.interval_combo = QComboBox()
        self.interval_combo.setFont(QFont("맑은 고딕", 9))
        self.interval_combo.addItems([
            "즉시 실행 (1회만 실행)",
            "10분마다 자동 수집",
            "30분마다 자동 수집",
            "1시간마다 자동 수집",
            "2시간마다 자동 수집",
            "3시간마다 자동 수집",
            "6시간마다 자동 수집",
            "12시간마다 자동 수집",
            "24시간마다 자동 수집"
        ])
        self.interval_values = [0, 10, 30, 60, 120, 180, 360, 720, 1440]
        
        interval_layout.addWidget(interval_lbl)
        interval_layout.addWidget(self.interval_combo)
        interval_layout.addStretch()
        settings_layout.addLayout(interval_layout)

        # 날짜 구간 설정
        date_box = QGroupBox("수집 날짜 / 구간 설정")
        date_layout = QVBoxLayout(date_box)
        date_layout.setContentsMargins(12, 12, 12, 12)
        date_layout.setSpacing(8)

        mode_layout = QHBoxLayout()
        self.radio_today = QRadioButton("당일 (오늘)")
        self.radio_single = QRadioButton("특정 날짜 수집")
        self.radio_range = QRadioButton("날짜 구간 수집")
        for r in [self.radio_today, self.radio_single, self.radio_range]:
            r.setCursor(Qt.PointingHandCursor)
            mode_layout.addWidget(r)
        mode_layout.addStretch()
        date_layout.addLayout(mode_layout)

        picker_layout = QHBoxLayout()
        picker_layout.setSpacing(8)
        
        self.single_date_picker = QDateEdit(QDate.currentDate())
        self.start_date_picker = QDateEdit(QDate.currentDate())
        self.end_date_picker = QDateEdit(QDate.currentDate())
        
        for p in [self.single_date_picker, self.start_date_picker, self.end_date_picker]:
            p.setCalendarPopup(True)
            p.setDisplayFormat("yyyy-MM-dd")

        self.single_lbl = QLabel("대상 일자:")
        self.range_lbl1 = QLabel("시작일:")
        self.range_lbl2 = QLabel("종료일:")

        picker_layout.addWidget(self.single_lbl)
        picker_layout.addWidget(self.single_date_picker)
        picker_layout.addWidget(self.range_lbl1)
        picker_layout.addWidget(self.start_date_picker)
        picker_layout.addWidget(self.range_lbl2)
        picker_layout.addWidget(self.end_date_picker)
        picker_layout.addStretch()
        date_layout.addLayout(picker_layout)

        settings_layout.addWidget(date_box)

        # 텔레그램 설정
        tg_box = QGroupBox("텔레그램 결과 알림 설정")
        tg_layout = QVBoxLayout(tg_box)
        tg_layout.setContentsMargins(12, 12, 12, 12)
        tg_layout.setSpacing(8)

        self.tg_enable_cb = QCheckBox("텔레그램 메시지 자동 전송 활성화")
        self.tg_enable_cb.setCursor(Qt.PointingHandCursor)
        tg_layout.addWidget(self.tg_enable_cb)

        tg_field_layout = QHBoxLayout()
        tg_field_layout.setSpacing(8)
        
        tok_lbl = QLabel("봇 토큰:")
        tok_lbl.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.tg_token_edit = QLineEdit()

        chat_lbl = QLabel("챗 ID:")
        chat_lbl.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        self.tg_chat_id_edit = QLineEdit()

        test_tg_btn = QPushButton("🚀 테스트 전송")
        test_tg_btn.setFont(QFont("맑은 고딕", 9, QFont.Bold))
        test_tg_btn.setCursor(Qt.PointingHandCursor)
        test_tg_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8EAF6;
                color: #283593;
                border: 1px solid #C5CAE9;
                border-radius: 6px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #C5CAE9;
            }
        """)
        test_tg_btn.clicked.connect(self._test_telegram)

        tg_field_layout.addWidget(tok_lbl)
        tg_field_layout.addWidget(self.tg_token_edit)
        tg_field_layout.addWidget(chat_lbl)
        tg_field_layout.addWidget(self.tg_chat_id_edit)
        tg_field_layout.addWidget(test_tg_btn)
        tg_layout.addLayout(tg_field_layout)

        settings_layout.addWidget(tg_box)
        main_layout.addWidget(settings_group)

        # 4. 제어 버튼 바
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(12)
        
        self.start_btn = QPushButton("▶ 수집 시작")
        self.stop_btn = QPushButton("■ 중지")
        
        for btn in [self.start_btn, self.stop_btn]:
            btn.setFont(QFont("맑은 고딕", 12, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(52)
        
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1B5E20;
            }
            QPushButton:disabled {
                background-color: #A5D6A7;
            }
        """)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
            QPushButton:disabled {
                background-color: #EF9A9A;
            }
        """)
        
        self.start_btn.clicked.connect(self._start_schedule)
        self.stop_btn.clicked.connect(self._stop_schedule)
        self.stop_btn.setEnabled(False)

        ctrl_bar.addWidget(self.start_btn)
        ctrl_bar.addWidget(self.stop_btn)
        main_layout.addLayout(ctrl_bar)

        # 5. 실행 로그 패널 (stretch=1 부여로 수직 높이를 크게 확장)
        self.log_panel = PyQtLogPanel()
        main_layout.addWidget(self.log_panel, stretch=1)

    def _connect_ui_signals(self):
        self.enable_download_cb.stateChanged.connect(self._save_ui_to_config)
        self.enable_ai_summary_cb.stateChanged.connect(self._save_ui_to_config)
        self.gemini_key_edit.editingFinished.connect(self._save_ui_to_config)

        for cb in self.site_checkboxes.values():
            cb.stateChanged.connect(self._save_ui_to_config)

        self.save_dir_edit.editingFinished.connect(self._save_ui_to_config)
        self.auto_subfolder_cb.stateChanged.connect(self._save_ui_to_config)
        self.interval_combo.currentIndexChanged.connect(self._save_ui_to_config)

        self.radio_today.toggled.connect(self._on_date_mode_changed)
        self.radio_single.toggled.connect(self._on_date_mode_changed)
        self.radio_range.toggled.connect(self._on_date_mode_changed)

        self.single_date_picker.dateChanged.connect(self._save_ui_to_config)
        self.start_date_picker.dateChanged.connect(self._save_ui_to_config)
        self.end_date_picker.dateChanged.connect(self._save_ui_to_config)

        self.tg_enable_cb.stateChanged.connect(self._save_ui_to_config)
        self.tg_token_edit.editingFinished.connect(self._save_ui_to_config)
        self.tg_chat_id_edit.editingFinished.connect(self._save_ui_to_config)

    def _select_all_sites(self):
        for cb in self.site_checkboxes.values():
            cb.setChecked(True)
        self._save_ui_to_config()

    def _deselect_all_sites(self):
        for cb in self.site_checkboxes.values():
            cb.setChecked(False)
        self._save_ui_to_config()

    def _browse_save_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.save_dir_edit.text())
        if dir_path:
            self.save_dir_edit.setText(dir_path)
            self._save_ui_to_config()

    def _on_date_mode_changed(self):
        is_single = self.radio_single.isChecked()
        is_range = self.radio_range.isChecked()

        self.single_lbl.setVisible(is_single)
        self.single_date_picker.setVisible(is_single)

        self.range_lbl1.setVisible(is_range)
        self.start_date_picker.setVisible(is_range)
        self.range_lbl2.setVisible(is_range)
        self.end_date_picker.setVisible(is_range)
        
        if not self._is_loading_config:
            self._save_ui_to_config()

    def _load_config_to_ui(self):
        c = self.config
        self.enable_download_cb.setChecked(c.enable_report_download)
        self.enable_ai_summary_cb.setChecked(c.enable_ai_summary)
        self.gemini_key_edit.setText(c.gemini_api_key)

        for site_key, cb in self.site_checkboxes.items():
            cb.setChecked(c.selected_sites.get(site_key, True))

        self.save_dir_edit.setText(str(c.save_dir))
        self.auto_subfolder_cb.setChecked(c.use_date_folder)

        if c.interval_minutes in self.interval_values:
            idx = self.interval_values.index(c.interval_minutes)
            self.interval_combo.setCurrentIndex(idx)
        else:
            self.interval_combo.setCurrentIndex(0)

        if c.date_mode == "single":
            self.radio_single.setChecked(True)
        elif c.date_mode == "range":
            self.radio_range.setChecked(True)
        else:
            self.radio_today.setChecked(True)

        if c.single_date:
            d = c.single_date if isinstance(c.single_date, date) else datetime.strptime(str(c.single_date), "%Y-%m-%d").date()
            self.single_date_picker.setDate(QDate(d.year, d.month, d.day))
        if c.start_date:
            d = c.start_date if isinstance(c.start_date, date) else datetime.strptime(str(c.start_date), "%Y-%m-%d").date()
            self.start_date_picker.setDate(QDate(d.year, d.month, d.day))
        if c.end_date:
            d = c.end_date if isinstance(c.end_date, date) else datetime.strptime(str(c.end_date), "%Y-%m-%d").date()
            self.end_date_picker.setDate(QDate(d.year, d.month, d.day))

        self.tg_enable_cb.setChecked(c.telegram_enabled)
        self.tg_token_edit.setText(c.telegram_token)
        self.tg_chat_id_edit.setText(c.telegram_chat_id)

        self._on_date_mode_changed()

    def _save_ui_to_config(self):
        if getattr(self, '_is_loading_config', False):
            return

        c = self.config
        c.enable_report_download = self.enable_download_cb.isChecked()
        c.enable_ai_summary = self.enable_ai_summary_cb.isChecked()
        c.gemini_api_key = self.gemini_key_edit.text().strip()

        for site_key, cb in self.site_checkboxes.items():
            c.selected_sites[site_key] = cb.isChecked()

        c.save_dir = Path(self.save_dir_edit.text().strip())
        c.use_date_folder = self.auto_subfolder_cb.isChecked()

        idx = self.interval_combo.currentIndex()
        if 0 <= idx < len(self.interval_values):
            c.interval_minutes = self.interval_values[idx]

        if self.radio_single.isChecked():
            c.date_mode = "single"
        elif self.radio_range.isChecked():
            c.date_mode = "range"
        else:
            c.date_mode = "today"

        q_single = self.single_date_picker.date()
        c.single_date = date(q_single.year(), q_single.month(), q_single.day())

        q_start = self.start_date_picker.date()
        c.start_date = date(q_start.year(), q_start.month(), q_start.day())

        q_end = self.end_date_picker.date()
        c.end_date = date(q_end.year(), q_end.month(), q_end.day())

        c.telegram_enabled = self.tg_enable_cb.isChecked()
        c.telegram_token = self.tg_token_edit.text().strip()
        c.telegram_chat_id = self.tg_chat_id_edit.text().strip()

        c.save_to_json()

    def _test_telegram(self):
        self._save_ui_to_config()
        if not self.config.telegram_token or not self.config.telegram_chat_id:
            QMessageBox.warning(self, "경고", "텔레그램 봇 토큰과 챗 ID를 먼저 입력하세요.")
            return

        success, err = send_telegram_message(self.config.telegram_token, self.config.telegram_chat_id, "📱 <b>[테스트] 증권사 리포트 수집기 텔레그램 연동 성공!</b>")
        if success:
            QMessageBox.information(self, "성공", "텔레그램 테스트 메시지가 성공적으로 전송되었습니다.")
        else:
            QMessageBox.critical(self, "실패", f"텔레그램 전송 실패:\n{err}")

    def _start_schedule(self):
        self._save_ui_to_config()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.scheduler.start()

    def _stop_schedule(self):
        self.scheduler.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

def run_qt_app():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = StockReportQtApp()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_qt_app()
