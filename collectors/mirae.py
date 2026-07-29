import time
import requests
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime
from typing import Callable
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from collectors.base import BaseCollector
from utils import USER_AGENT, format_date, clean_filename, parse_company_and_title, is_similar_file_exists

class MiraeCollector(BaseCollector):
    def __init__(self):
        super().__init__("미래에셋증권", "미래에셋증권")

    def fetch(self, save_dir: Path, target_dt: datetime, log_fn: Callable[[str], None]) -> int:
        date_formats = format_date(target_dt)
        today_dot = date_formats['dot_date']
        today_dash = today_dot.replace('.', '-')
        log_fn(f"📌  --- [미래에셋증권] 수집 시작 ({today_dot}) ---")
        
        url = "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521"
        count = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)

                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                rows = soup.select("table tbody tr")

                for row in rows:
                    row_text = row.get_text()
                    if today_dot not in row_text and today_dash not in row_text:
                        continue

                    a_tags = row.select("a")
                    if not a_tags:
                        continue

                    raw_title_text = a_tags[0].get_text(strip=True)
                    if not raw_title_text:
                        continue

                    company, title = parse_company_and_title(raw_title_text)
                    if company:
                        raw_file_name = f"[{company}] {title}.pdf" if title else f"[{company}].pdf"
                    else:
                        raw_file_name = f"[{raw_title_text}].pdf"

                    file_name = clean_filename(raw_file_name)
                    save_path = save_dir / file_name

                    if save_path.exists():
                        log_fn(f"📁  [스킵] {file_name}")
                        continue
                        
                    if is_similar_file_exists(save_dir, file_name, 0.95):
                        log_fn(f"📁  [유사 스킵(95%+)] {file_name}")
                        continue

                    pdf_url = None
                    for a in a_tags:
                        href = a.get("href", "")
                        import re
                        match = re.search(r"downConfirm\s*\(\s*['\"]([^'\"]+)['\"]", href)
                        if match:
                            pdf_url = match.group(1)
                            break
                        elif ".pdf" in href:
                            pdf_url = urljoin(url, href)
                            break

                    if pdf_url:
                        try:
                            r = requests.get(pdf_url, headers={"User-Agent": USER_AGENT}, timeout=15)
                            if r.status_code == 200 and len(r.content) > 1000:
                                with open(save_path, "wb") as f:
                                    f.write(r.content)
                                log_fn(f"✅  [성공] {file_name}")
                                count += 1
                        except Exception as e:
                            log_fn(f"❌  [다운로드 실패] {file_name}: {e}")

            except Exception as e:
                log_fn(f"⚠️  미래에셋 접속/파싱 오류: {e}")
            finally:
                browser.close()

        log_fn(f"✅  미래에셋증권 완료 (신규 {count}개 다운로드)\n")
        return count
