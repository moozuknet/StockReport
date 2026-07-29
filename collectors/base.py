import os
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Callable

# Playwright가 PyInstaller EXE 환경에서도 윈도우 사용자 폴더(%USERPROFILE%\AppData\Local\ms-playwright)를 절대경로로 참조하도록 설정
ms_playwright_path = Path.home() / "AppData" / "Local" / "ms-playwright"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ms_playwright_path)

class BaseCollector(ABC):
    def __init__(self, name: str, config_key: str):
        self.name = name
        self.config_key = config_key

    @abstractmethod
    def fetch(self, save_dir: Path, target_dt: datetime, log_fn: Callable[[str], None]) -> int:
        """지정된 대상 날짜(target_dt)의 리포트를 수집하여 save_dir에 저장합니다."""
        pass
