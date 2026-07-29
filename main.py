import os
import sys
from pathlib import Path

# Playwright가 PyInstaller EXE 환경에서도 윈도우 사용자 폴더(%USERPROFILE%\AppData\Local\ms-playwright)를 절대경로로 참조하도록 설정
ms_playwright_path = Path.home() / "AppData" / "Local" / "ms-playwright"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ms_playwright_path)

from ui.app_qt import run_qt_app

if __name__ == "__main__":
    run_qt_app()
