import tkinter as tk
import ttkbootstrap as ttk
from typing import Optional
from config import AppConfig
from collectors import CollectorManager
from scheduler import ReportScheduler
from ui.site_selector import SiteSelectorFrame
from ui.settings_panel import SettingsPanelFrame
from ui.log_panel import LogPanelFrame

class StockReportApp(ttk.Window):
    def __init__(self):
        super().__init__(
            title="통합 증권 리포트 수집기 (스케줄러 & 텔레그램 연동)", 
            themename="flatly",  # 다크 테마 제거, 깨끗한 라이트 테마 적용
            size=(820, 800),
            resizable=(True, True)
        )
        self.minsize(760, 700)

        # 저장된 settings.json 자동 로드
        self.config = AppConfig.load_from_json()
        self.collector_manager = CollectorManager()
        self.scheduler: Optional[ReportScheduler] = None

        self._build_ui()
        self._bring_to_front()

    def _bring_to_front(self):
        self.deiconify()
        self.state('normal')
        try:
            self.position_center()
        except Exception:
            self.geometry("820x800+150+150")
        self.lift()
        self.attributes('-topmost', True)
        self.after(500, lambda: self.attributes('-topmost', False))
        self.focus_force()

    def _build_ui(self):
        # 상단 헤더
        header_label = ttk.Label(
            self, 
            text="📊 증권사별 리포트 자동 수집기", 
            font=("Malgun Gothic", 14, "bold"),
            bootstyle="primary"
        )
        header_label.pack(pady=(10, 2))

        # 1. 사이트 선택 프레임 (상단)
        self.site_selector = SiteSelectorFrame(self, self.config)
        self.site_selector.pack(fill=tk.X, padx=12, pady=4)

        # 2. 실시간 로그 프레임 (하단 선배치 또는 하단 스케일 조정)
        self.log_panel = LogPanelFrame(self)

        # 3. 저장 경로, 날짜 선택 & 텔레그램 설정 프레임 (중단)
        self.settings_panel = SettingsPanelFrame(
            self, 
            self.config, 
            on_start=self.start_collection, 
            on_stop=self.stop_collection,
            log_fn=self.safe_log
        )
        self.settings_panel.pack(fill=tk.X, padx=12, pady=4)

        # 4. 로그 프레임 배치
        self.log_panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))

    def safe_log(self, message: str):
        """스레드 안전하게 로그 영역에 메시지를 기록합니다."""
        self.after(0, lambda: self.log_panel.log(message))

    def start_collection(self):
        active_names = self.collector_manager.get_active_collector_names(self.config)
        if not active_names:
            self.safe_log("⚠️ [경고] 수집 대상 사이트가 선택되지 않았습니다.")
            self.settings_panel.set_stopped_state()
            return

        self.safe_log(f"🚀 선택된 수집 대상 사이트: {', '.join(active_names)}")
        target_dates = self.config.get_target_dates()
        d_strs = [d.strftime("%Y-%m-%d") for d in target_dates]
        self.safe_log(f"📅 수집 대상 일자 ({len(target_dates)}개): {', '.join(d_strs)}")
        
        # 최신 설정 저장
        self.config.save_to_json()

        self.scheduler = ReportScheduler(
            config=self.config,
            log_fn=self.safe_log,
            runner_fn=self.run_cycle
        )
        self.scheduler.start()

    def run_cycle(self, config: AppConfig, logger):
        self.collector_manager.run(config, logger)
        if config.interval_minutes == 0:
            self.after(0, self.settings_panel.set_stopped_state)

    def stop_collection(self):
        if self.scheduler:
            self.scheduler.stop()
            self.scheduler = None

    def on_closing(self):
        self.config.save_to_json()
        if self.scheduler:
            self.scheduler.stop()
        self.destroy()
