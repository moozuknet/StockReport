import os
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Callable

# Playwright가 PyInstaller EXE 환경에서도 윈도우 사용자 폴더(%USERPROFILE%\AppData\Local\ms-playwright)를 절대경로로 참조하도록 설정
ms_playwright_path = Path.home() / "AppData" / "Local" / "ms-playwright"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ms_playwright_path)

def launch_playwright_browser(p, headless: bool = True):
    """
    Playwright 브라우저 실행 보조 함수:
    1. 기본 p.chromium.launch(headless=headless) 시도
    2. chromium_headless_shell 미설치 예외 발생 시 시스템 설치된 Google Chrome (channel='chrome') 폴백 시도
    3. 실패 시 Microsoft Edge (channel='msedge') 폴백 시도
    """
    try:
        return p.chromium.launch(headless=headless)
    except Exception as e:
        err_msg = str(e)
        if "Executable doesn't exist" in err_msg or "chrome-headless-shell" in err_msg or "Playwright was just installed" in err_msg:
            # 1차 폴백: 시스템 Google Chrome
            try:
                return p.chromium.launch(headless=headless, channel="chrome")
            except Exception:
                pass
            # 2차 폴백: 시스템 Microsoft Edge (윈도우 10/11 기본 탑재)
            try:
                return p.chromium.launch(headless=headless, channel="msedge")
            except Exception:
                pass
        raise e

class BaseCollector(ABC):
    def __init__(self, name: str, config_key: str):
        self.name = name
        self.config_key = config_key

    @abstractmethod
    def fetch(self, save_dir: Path, target_dt: datetime, log_fn: Callable[[str], None]) -> int:
        """지정된 대상 날짜(target_dt)의 리포트를 수집하여 save_dir에 저장합니다."""
        pass
