import tkinter as tk
import ttkbootstrap as ttk
from typing import Dict
from config import AppConfig

SITE_DISPLAY_NAMES = [
    ("교보증권", "교보증권"),
    ("미래에셋증권", "미래에셋증권"),
    ("한경 컨센서스", "한경 컨센서스"),
    ("네이버_기업분석", "네이버 (기업분석)"),
    ("네이버_산업분석", "네이버 (산업분석)"),
    ("네이버_경제분석", "네이버 (경제분석)"),
    ("네이버_시장분석", "네이버 (시장분석)"),
    ("네이버_투자정보", "네이버 (투자정보)"),
]

class SiteSelectorFrame(ttk.LabelFrame):
    def __init__(self, master, config: AppConfig, **kwargs):
        super().__init__(master, text=" 📌 수집 대상 사이트 선택 ", **kwargs)
        self.config = config
        self.vars: Dict[str, tk.BooleanVar] = {}

        self._build_ui()

    def _build_ui(self):
        # 상단 버튼 영역 (전체선택 / 해제)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        select_all_btn = ttk.Button(btn_frame, text="전체 선택", bootstyle="outline-primary", command=self.select_all, width=10)
        select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

        deselect_all_btn = ttk.Button(btn_frame, text="전체 해제", bootstyle="outline-secondary", command=self.deselect_all, width=10)
        deselect_all_btn.pack(side=tk.LEFT)

        # 체크박스 그리드 영역 (2열 구성)
        grid_frame = ttk.Frame(self)
        grid_frame.pack(fill=tk.X)

        for idx, (config_key, display_label) in enumerate(SITE_DISPLAY_NAMES):
            row = idx // 2
            col = idx % 2

            var = tk.BooleanVar(value=self.config.selected_sites.get(config_key, True))
            self.vars[config_key] = var

            cb = ttk.Checkbutton(
                grid_frame, 
                text=display_label, 
                variable=var,
                command=self.update_config,
                bootstyle="round-toggle"
            )
            cb.grid(row=row, column=col, sticky=tk.W, padx=15, pady=4)

    def select_all(self):
        for var in self.vars.values():
            var.set(True)
        self.update_config()

    def deselect_all(self):
        for var in self.vars.values():
            var.set(False)
        self.update_config()

    def update_config(self):
        for config_key, var in self.vars.items():
            self.config.selected_sites[config_key] = var.get()
