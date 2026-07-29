import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.widgets import DateEntry
from datetime import datetime, date
from pathlib import Path
from config import AppConfig, send_telegram_message

INTERVAL_OPTIONS = [
    ("즉시 실행 (1회만)", 0),
    ("10분 마다 반복", 10),
    ("30분 마다 반복", 30),
    ("1시간 마다 반복", 60),
    ("2시간 마다 반복", 120),
    ("3시간 마다 반복", 180),
    ("6시간 마다 반복", 360),
]

class SettingsPanelFrame(ttk.LabelFrame):
    def __init__(self, master, config: AppConfig, on_start, on_stop, log_fn, **kwargs):
        super().__init__(master, text=" ⚙️ 저장 경로, 날짜 & 텔레그램 설정 ", **kwargs)
        self.config = config
        self.on_start = on_start
        self.on_stop = on_stop
        self.log_fn = log_fn

        self._build_ui()

    def _build_ui(self):
        # 1. 저장 경로 섹션
        dir_frame = ttk.Frame(self)
        dir_frame.pack(fill=tk.X, padx=10, pady=(8, 4))

        ttk.Label(dir_frame, text="저장 폴더: ", width=10).pack(side=tk.LEFT)

        self.dir_entry = ttk.Entry(dir_frame)
        self.dir_entry.insert(0, str(self.config.save_dir))
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = ttk.Button(dir_frame, text="폴더 찾아보기", bootstyle="info-outline", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT)

        # 날짜별 하위 폴더 옵션
        self.subfolder_var = tk.BooleanVar(value=self.config.use_date_folder)
        subfolder_cb = ttk.Checkbutton(
            self, 
            text="날짜별 하위 폴더 자동 생성 (예: Downloads/20260729)", 
            variable=self.subfolder_var,
            command=self.update_config
        )
        subfolder_cb.pack(anchor=tk.W, padx=10, pady=(0, 8))

        # 2. 📅 날짜 수집 범위 (달력 UI) 섹션
        date_group = ttk.LabelFrame(self, text=" 📅 수집 날짜 / 구간 설정 ")
        date_group.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.date_mode_var = tk.StringVar(value=self.config.date_mode)

        r_frame = ttk.Frame(date_group)
        r_frame.pack(fill=tk.X, padx=10, pady=5)

        r_today = ttk.Radiobutton(r_frame, text="당일 (오늘)", variable=self.date_mode_var, value="today", command=self.on_date_mode_change)
        r_today.pack(side=tk.LEFT, padx=(0, 15))

        r_single = ttk.Radiobutton(r_frame, text="특정 날짜 수집", variable=self.date_mode_var, value="single", command=self.on_date_mode_change)
        r_single.pack(side=tk.LEFT, padx=(0, 15))

        r_range = ttk.Radiobutton(r_frame, text="날짜 구간 수집", variable=self.date_mode_var, value="range", command=self.on_date_mode_change)
        r_range.pack(side=tk.LEFT)

        picker_frame = ttk.Frame(date_group)
        picker_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.single_label = ttk.Label(picker_frame, text="선택 날짜: ")
        self.single_date_entry = DateEntry(picker_frame, dateformat="%Y-%m-%d", bootstyle="primary", width=12)

        self.range_start_label = ttk.Label(picker_frame, text="시작일: ")
        self.start_date_entry = DateEntry(picker_frame, dateformat="%Y-%m-%d", bootstyle="info", width=12)

        self.range_end_label = ttk.Label(picker_frame, text=" ~ 종료일: ")
        self.end_date_entry = DateEntry(picker_frame, dateformat="%Y-%m-%d", bootstyle="info", width=12)

        self.on_date_mode_change()

        # 3. 📱 텔레그램 알림 설정 섹션
        tg_group = ttk.LabelFrame(self, text=" 📱 텔레그램 결과 알림 설정 ")
        tg_group.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.tg_enable_var = tk.BooleanVar(value=self.config.telegram_enabled)
        tg_cb = ttk.Checkbutton(
            tg_group, 
            text="텔레그램 메시지 자동 전송 활성화", 
            variable=self.tg_enable_var,
            command=self.update_config
        )
        tg_cb.pack(anchor=tk.W, padx=10, pady=(5, 5))

        tg_inputs = ttk.Frame(tg_group)
        tg_inputs.pack(fill=tk.X, padx=10, pady=(0, 8))

        ttk.Label(tg_inputs, text="봇 토큰:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.tg_token_entry = ttk.Entry(tg_inputs, width=32)
        self.tg_token_entry.insert(0, self.config.telegram_token)
        self.tg_token_entry.grid(row=0, column=1, padx=(0, 15))

        ttk.Label(tg_inputs, text="챗 ID:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.tg_chat_entry = ttk.Entry(tg_inputs, width=18)
        self.tg_chat_entry.insert(0, self.config.telegram_chat_id)
        self.tg_chat_entry.grid(row=0, column=3, padx=(0, 10))

        test_tg_btn = ttk.Button(tg_inputs, text="🧪 테스트 전송", bootstyle="secondary-outline", command=self.test_telegram, width=12)
        test_tg_btn.grid(row=0, column=4)

        # 4. 동작 주기 및 제어 버튼 섹션
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        ttk.Label(ctrl_frame, text="동작 주기: ", width=10).pack(side=tk.LEFT)

        self.interval_combo = ttk.Combobox(
            ctrl_frame, 
            values=[opt[0] for opt in INTERVAL_OPTIONS], 
            state="readonly",
            width=18
        )
        # 저장된 interval_minutes에 맞춰 초기값 세팅
        matched_idx = 0
        for idx, opt in enumerate(INTERVAL_OPTIONS):
            if opt[1] == self.config.interval_minutes:
                matched_idx = idx
                break
        self.interval_combo.current(matched_idx)
        self.interval_combo.bind("<<ComboboxSelected>>", self.on_interval_change)
        self.interval_combo.pack(side=tk.LEFT, padx=(0, 15))

        # 제어 버튼
        self.start_btn = ttk.Button(ctrl_frame, text="▶ 수집 시작", bootstyle="success", command=self.handle_start, width=12)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(ctrl_frame, text="■ 중지", bootstyle="danger", command=self.handle_stop, state=tk.DISABLED, width=8)
        self.stop_btn.pack(side=tk.LEFT)

    def on_date_mode_change(self):
        mode = self.date_mode_var.get()
        self.config.date_mode = mode
        
        self.single_label.pack_forget()
        self.single_date_entry.pack_forget()
        self.range_start_label.pack_forget()
        self.start_date_entry.pack_forget()
        self.range_end_label.pack_forget()
        self.end_date_entry.pack_forget()

        if mode == "single":
            self.single_label.pack(side=tk.LEFT, padx=(0, 5))
            self.single_date_entry.pack(side=tk.LEFT)
        elif mode == "range":
            self.range_start_label.pack(side=tk.LEFT, padx=(0, 5))
            self.start_date_entry.pack(side=tk.LEFT)
            self.range_end_label.pack(side=tk.LEFT, padx=(5, 5))
            self.end_date_entry.pack(side=tk.LEFT)

    def browse_directory(self):
        chosen = filedialog.askdirectory(initialdir=self.config.save_dir, title="리포트 저장 폴더 선택")
        if chosen:
            chosen_path = Path(chosen)
            self.config.save_dir = chosen_path
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, str(chosen_path))
            self.update_config()

    def update_config(self):
        try:
            self.config.save_dir = Path(self.dir_entry.get().strip())
        except Exception:
            pass
        
        self.config.use_date_folder = self.subfolder_var.get()
        self.config.date_mode = self.date_mode_var.get()

        if self.config.date_mode == "single":
            try:
                s = self.single_date_entry.entry.get()
                self.config.single_date = datetime.strptime(str(s), "%Y-%m-%d").date()
            except Exception:
                pass

        elif self.config.date_mode == "range":
            try:
                s = self.start_date_entry.entry.get()
                self.config.start_date = datetime.strptime(str(s), "%Y-%m-%d").date()
            except Exception:
                pass

            try:
                e = self.end_date_entry.entry.get()
                self.config.end_date = datetime.strptime(str(e), "%Y-%m-%d").date()
            except Exception:
                pass

        self.config.telegram_enabled = self.tg_enable_var.get()
        self.config.telegram_token = self.tg_token_entry.get().strip()
        self.config.telegram_chat_id = self.tg_chat_entry.get().strip()

        # 자동 json 저장
        self.config.save_to_json()

    def test_telegram(self):
        self.update_config()
        token = self.config.telegram_token
        chat_id = self.config.telegram_chat_id
        self.log_fn("📱 텔레그램 테스트 메시지 전송 시도 중...")
        success, msg = send_telegram_message(
            token, 
            chat_id, 
            "<b>🧪 [증권 리포트 수집기]</b>\n텔레그램 연동 테스트 메시지입니다! ✅"
        )
        if success:
            self.log_fn("📱 텔레그램 테스트 메시지 전송 성공! ✅")
        else:
            self.log_fn(f"📱 텔레그램 테스트 메시지 실패: {msg} ⚠️")

    def on_interval_change(self, event=None):
        selected_idx = self.interval_combo.current()
        self.config.interval_minutes = INTERVAL_OPTIONS[selected_idx][1]
        self.config.save_to_json()

    def handle_start(self):
        self.update_config()
        self.start_btn.config(state=tk.DISABLED)
        self.interval_combo.config(state="disabled")
        self.stop_btn.config(state=tk.NORMAL)
        self.on_start()

    def handle_stop(self):
        self.on_stop()
        self.set_stopped_state()

    def set_stopped_state(self):
        self.start_btn.config(state=tk.NORMAL)
        self.interval_combo.config(state="readonly")
        self.stop_btn.config(state=tk.DISABLED)
