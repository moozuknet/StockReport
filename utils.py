import re
import difflib
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def clean_filename(filename: str) -> str:
    """파일명에서 윈도우/OS 금지 특수문자를 제거하고 다중 공백을 정돈합니다."""
    cleaned = re.sub(r'[\\\\/*?:"<>|]', '', filename)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def format_date(dt: datetime = None) -> Dict[str, str]:
    """날짜 객체를 수집기별 날짜 문자열 포맷 딕셔너리로 반환합니다."""
    if dt is None:
        dt = datetime.now()
    return {
        'folder_name': dt.strftime("%Y%m%d"),
        'naver_date': dt.strftime("%y.%m.%d"),
        'dot_date': dt.strftime("%Y.%m.%d"),
        'slash_date': dt.strftime("%Y/%m/%d")
    }

def parse_company_and_title(raw_text: str) -> Tuple[str, str]:
    """'종목명 (코드) 제목' 문장 패턴에서 종목명과 제목을 파싱합니다."""
    match = re.match(r"^([^(]+)\s*\([^)]*\)\s*(.*)$", raw_text)
    if match:
        company = match.group(1).strip()
        title = match.group(2).strip()
        return company, title
    return "", raw_text.strip()

def is_similar_file_exists(save_dir: Path, new_filename: str, threshold: float = 0.95) -> bool:
    """지정된 디렉토리 내에 유사도 threshold 이상의 파일이 이미 존재하는지 검사합니다."""
    if not save_dir.exists():
        return False

    for existing_file in save_dir.iterdir():
        if not existing_file.is_file():
            continue

        similarity = difflib.SequenceMatcher(None, new_filename, existing_file.name).ratio()
        if similarity >= threshold:
            return True
    return False
