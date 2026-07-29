import re
import time
from pathlib import Path
from datetime import datetime
from typing import Callable
from collectors.base import BaseCollector, launch_playwright_browser
from utils import USER_AGENT, format_date, clean_filename, is_similar_file_exists

class KyoboCollector(BaseCollector):
    def __init__(self):
        super().__init__("교보증권", "교보증권")

    def fetch(self, save_dir: Path, target_dt: datetime, log_fn: Callable[[str], None]) -> int:
        date_formats = format_date(target_dt)
        today_slash = date_formats['slash_date']
        today_dot = date_formats['dot_date']
        log_fn(f"📌  --- [교보증권] 수집 시작 ({today_dot}) ---")
        
        url = "https://www.iprovest.com/weblogic/RSReportServlet?scr_id=10&menuCode=1&srch_db=0&QU=&DT1=&DT2=&provestz=&pageNum=1"
        count = 0

        with sync_playwright() as p:
            browser = launch_playwright_browser(p)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(3)

                rows = page.locator("table tr")
                rows_count = rows.count()

                for i in range(rows_count):
                    row = rows.nth(i)
                    row_text = row.inner_text()

                    if today_slash not in row_text and today_dot not in row_text:
                        continue

                    tds = row.locator("td")
                    if tds.count() < 3:
                        continue

                    title_text = tds.nth(1).inner_text().strip().split('\n')[0]
                    item_text = tds.nth(2).inner_text().strip().split('\n')[0]
                    
                    if not title_text:
                        continue

                    if item_text:
                        if title_text.startswith(item_text):
                            title_text = re.sub(rf"^{re.escape(item_text)}[\s,;:]*", "", title_text).strip()
                        raw_file_name = f"[{item_text}] {title_text}.pdf"
                    else:
                        raw_file_name = f"{title_text}.pdf"
                        
                    file_name = clean_filename(raw_file_name)
                    save_path = save_dir / file_name

                    if save_path.exists():
                        log_fn(f"📁  [스킵] {file_name}")
                        continue
                        
                    if is_similar_file_exists(save_dir, file_name, 0.95):
                        log_fn(f"📁  [유사 스킵(95%+)] {file_name}")
                        continue

                    last_td = tds.last
                    download_btn = last_td.locator("a, button, img, span").first

                    if download_btn.count() > 0:
                        try:
                            with page.expect_download(timeout=7000) as download_info:
                                download_btn.click()
                            download = download_info.value
                            download.save_as(save_path)
                            log_fn(f"✅  [성공] {file_name}")
                            count += 1
                        except Exception as e:
                            log_fn(f"❌  [다운로드 실패] {file_name}: {e}")

            except Exception as e:
                log_fn(f"⚠️  교보증권 접속/파싱 오류: {e}")
            finally:
                browser.close()

        log_fn(f"✅  교보증권 완료 (신규 {count}개 다운로드)\n")
        return count
