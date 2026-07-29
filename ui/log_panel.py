import tkinter as tk
import ttkbootstrap as ttk
from datetime import datetime

class LogPanelFrame(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.success_count = 0
        self.skip_count = 0

        self._build_ui()

    def _build_ui(self):
        # 상단 타이틀 & 카운터 정보 바 (taxfile-automated 헤더 스타일)
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(2, 6))

        title_lbl = ttk.Label(top_bar, text="실행 로그", font=("맑은 고딕", 10, "bold"))
        title_lbl.pack(side=tk.LEFT)

        self.status_label = ttk.Label(top_bar, text="상태: 대기 중 ⏱️", bootstyle="info", font=("맑은 고딕", 9))
        self.status_label.pack(side=tk.LEFT, padx=(15, 0))

        clear_btn = ttk.Button(top_bar, text="🧹 로그 지우기", bootstyle="secondary-outline", command=self.clear_logs, width=12)
        clear_btn.pack(side=tk.RIGHT)

        # taxfile-automated 100% 동일한 하얀색 카드 프레임 내부의 다크 콘솔 박스 (#1E1E1E)
        card_frame = tk.Frame(self, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        card_frame.pack(fill=tk.BOTH, expand=True)

        self.console_container = tk.Frame(card_frame, bg="#1E1E1E", bd=0)
        self.console_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        scrollbar = ttk.Scrollbar(self.console_container, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # taxfile-automated(PySimpleGUI/Tkinter)와 100% 동일한 순수 Text 위젯
        # 커스텀 태그 수정을 하지 않고 순수 텍스트로 밀어 넣어야 윈도우 원색 멀티컬러 이모지가 100% 출력됩니다.
        self.log_area = tk.Text(
            self.console_container, 
            height=14, 
            font=("맑은 고딕", 9),
            spacing1=2,
            spacing3=2,
            bg="#1E1E1E", 
            fg="#FFFFFF",
            selectbackground="#264F78",
            selectforeground="#FFFFFF",
            insertbackground="white",
            highlightthickness=0,
            bd=0,
            yscrollcommand=scrollbar.set
        )
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=4)
        scrollbar.config(command=self.log_area.yview)

        self.apply_dark_console()
        self.after(10, self.apply_dark_console)
        self.after(50, self.apply_dark_console)
        self.after(200, self.apply_dark_console)

    def apply_dark_console(self):
        """ttkbootstrap 테마가 Text 배경색을 흰색으로 덮어쓰는 것을 방지합니다."""
        try:
            self.console_container.config(bg="#1E1E1E", background="#1E1E1E")
            self.log_area.config(
                bg="#1E1E1E", 
                fg="#FFFFFF", 
                background="#1E1E1E", 
                foreground="#FFFFFF",
                insertbackground="white",
                selectbackground="#264F78",
                selectforeground="#FFFFFF"
            )
        except Exception:
            pass

    def log(self, message: str):
        self.apply_dark_console()
        
        # 카운터 업데이트
        if "✅" in message or "[성공]" in message:
            self.success_count += 1
        if "📁" in message or "📄" in message or "[스킵]" in message:
            self.skip_count += 1

        # taxfile-automated 100% 동일 방식: 순수 타임스탬프 + 메시지 조합 출력
        timestamp = datetime.now().strftime("%H:%M:%S - ")
        full_line = f"{timestamp} {message}\n"

        self.log_area.insert(tk.END, full_line)
        self.log_area.see(tk.END)
        self.status_label.config(text=f"✅ 성공: {self.success_count}개 | 📁 중복 스킵: {self.skip_count}개")

    def clear_logs(self):
        self.log_area.delete("1.0", tk.END)
        self.success_count = 0
        self.skip_count = 0
        self.status_label.config(text="상태: 로그 초기화됨 🧹")
