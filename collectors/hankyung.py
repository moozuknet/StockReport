import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Callable
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from collectors.base import BaseCollector
from utils import USER_AGENT, format_date, clean_filename, parse_company_and_title, is_similar_file_exists

class HankyungCollector(BaseCollector):
    def __init__(self):
        super().__init__("한경 컨센서스", "한경 컨센서스")

    def fetch(self, save_dir: Path, target_dt: datetime, log_fn: Callable[[str], None]) -> int:
        date_formats = format_date(target_dt)
        today_dot = date_formats['dot_date']
        log_fn(f"📌  --- [한경 컨센서스] 수집 시작 ({today_dot}) ---")
        
        url = "https://markets.hankyung.com/consensus"
        download_targets = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            try:
                page.goto(url, wait_until="networkidle")
                page.wait_for_selector("table tr, div[class*='list']", timeout=15000)
                time.sleep(2)

                rows_count = page.locator("tr").count()

                for i in range(rows_count):
                    row = page.locator("tr").nth(i)
                    row_text = row.inner_text()

                    if today_dot not in row_text:
                        continue

                    category = "산업"
                    if "기업" in row_text:
                        category = "기업"
                    elif "산업" in row_text:
                        category = "산업"
                    elif "시장" in row_text:
                        category = "시장"
                    elif "경제" in row_text:
                        category = "경제"

                    a_tag = row.locator("a").first
                    if a_tag.count() == 0:
                        continue

                    raw_title = a_tag.inner_text().strip()
                    href = a_tag.get_attribute("href")

                    if raw_title and href:
                        download_targets.append({"category": category, "raw_title": raw_title, "href": href})
            except Exception as e:
                log_fn(f"⚠️  한경 목록 파싱 오류: {e}")
            finally:
                browser.close()

        hk_headers = {"User-Agent": USER_AGENT, "Referer": "https://markets.hankyung.com/consensus"}
        count = 0

        for item in download_targets:
            category, raw_title, href = item["category"], item["raw_title"], item["href"]

            if category == "기업":
                company, title = parse_company_and_title(raw_title)
                if company:
                    raw_file_name = f"[{company}] {title}.pdf" if title else f"[{company}].pdf"
                else:
                    raw_file_name = f"[{raw_title}].pdf"
            else:
                raw_file_name = f"[{category}] {raw_title}.pdf"

            file_name = clean_filename(raw_file_name)
            save_path = save_dir / file_name

            if save_path.exists():
                log_fn(f"📁  [스킵] {file_name}")
                continue
                
            if is_similar_file_exists(save_dir, file_name, 0.95):
                log_fn(f"📁  [유사 스킵(95%+)] {file_name}")
                continue

            pdf_url = href if href.endswith(".pdf") else None
            if not pdf_url:
                detail_url = href if href.startswith("http") else "https://markets.hankyung.com" + href
                try:
                    res = requests.get(detail_url, headers=hk_headers, timeout=10)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, 'html.parser')
                        pdf_elem = soup.select_one("a[href*='.pdf']") or soup.select_one("a.btn_download, a.btn-down, div.down a")
                        if pdf_elem and pdf_elem.get("href"):
                            pdf_url = pdf_elem.get("href")
                            if not pdf_url.startswith("http"):
                                pdf_url = "https://markets.hankyung.com" + pdf_url
                except Exception:
                    continue

            if pdf_url:
                try:
                    pdf_res = requests.get(pdf_url, headers=hk_headers, timeout=15)
                    if pdf_res.status_code == 200:
                        with open(save_path, 'wb') as f:
                            f.write(pdf_res.content)
                        log_fn(f"✅  [성공] {file_name}")
                        count += 1
                except Exception as e:
                    log_fn(f"❌  [실패] {file_name}: {e}")

        log_fn(f"✅  한경 컨센서스 완료 (신규 {count}개 다운로드)\n")
        return count
