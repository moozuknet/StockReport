import re
import requests
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime
from typing import Callable, List, Tuple
from bs4 import BeautifulSoup
from collectors.base import BaseCollector
from utils import USER_AGENT, format_date, clean_filename, is_similar_file_exists

NAVER_CATEGORIES: List[Tuple[str, str, str]] = [
    ("company_list.naver", "네이버_기업분석", "기업분석"),
    ("industry_list.naver", "네이버_산업분석", "산업분석"),
    ("economy_list.naver", "네이버_경제분석", "경제분석"),
    ("market_info_list.naver", "네이버_시장분석", "시장분석"),
    ("invest_list.naver", "네이버_투자정보", "투자정보")
]

class NaverCollector(BaseCollector):
    def __init__(self, sub_url: str, config_key: str, display_name: str):
        super().__init__(f"네이버증권({display_name})", config_key)
        self.sub_url = sub_url
        self.display_name = display_name

    def fetch(self, save_dir: Path, target_dt: datetime, log_fn: Callable[[str], None]) -> int:
        date_formats = format_date(target_dt)
        today_str = date_formats['naver_date']
        log_fn(f"🔍 > [{self.display_name}] 탐색 시작 ({today_str})...")
        
        base_url = f"https://finance.naver.com/research/{self.sub_url}"

        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Referer": "https://finance.naver.com/research/"
        })

        download_count = 0
        page = 1

        while page <= 20:
            try:
                resp = session.get(base_url, params={"page": page}, timeout=15)
                soup = BeautifulSoup(resp.text, "html.parser")
                
                rows = soup.select("table.type_1 tr")
                if not rows:
                    break

                found_today = False

                for row in rows:
                    cols = row.select("td")
                    if len(cols) < 3:
                        continue

                    row_text = row.get_text()
                    date_match = re.search(r'(\d{2}\.\d{2}\.\d{2})', row_text)
                    if not date_match:
                        continue

                    date_text = date_match.group(1)

                    if date_text == today_str:
                        found_today = True

                        if self.display_name == "기업분석":
                            prefix_a = cols[0].select_one("a")
                            prefix = prefix_a.get_text(strip=True) if prefix_a else "기업"
                            title_a = cols[1].select_one("a")
                        elif self.display_name == "산업분석":
                            prefix = cols[0].get_text(" ", strip=True) or "산업"
                            title_a = cols[1].select_one("a")
                        else:
                            prefix = self.display_name.replace("분석", "")
                            title_a = cols[0].select_one("a")

                        pdf_a = row.select_one("a[href*='.pdf'], td.file a")

                        if not title_a or not pdf_a:
                            continue

                        title = title_a.get_text(" ", strip=True)
                        if title_a.has_attr("title") and title_a["title"].strip():
                            title = title_a["title"].strip()

                        # 말줄임표 처리 및 상세 페이지 진입
                        if title.endswith("..") or title.endswith("..."):
                            detail_href = title_a.get("href")
                            if detail_href:
                                try:
                                    detail_url = urljoin(base_url, detail_href)
                                    detail_resp = session.get(detail_url, timeout=10)
                                    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                                    
                                    full_title_elem = detail_soup.select_one("th.view_sbj, div.view_sbj, span.view_sbj, .view_sbj")
                                    if full_title_elem:
                                        for child in full_title_elem.find_all(['span', 'div', 'p', 'em', 'td', 'th']):
                                            child_text = child.get_text()
                                            if re.search(r'\d{2,4}\.\d{2}\.\d{2}', child_text) or '조회' in child_text:
                                                child.extract()
                                                
                                        raw_title = full_title_elem.get_text(" ", strip=True)
                                        meta_match = re.search(r'(\s+[^\s]+)\s*\|\s*\d{2,4}\.\d{2}\.\d{2}\s*\|', raw_title)
                                        if meta_match:
                                            raw_title = raw_title[:meta_match.start()].strip()
                                            
                                        title = raw_title
                                except Exception as e:
                                    log_fn(f"⚠️  [네이버 상세 파싱 예외] {e}")

                        pdf_href = pdf_a.get("href", "").strip()

                        raw_file_name = f"[{prefix}] {title}.pdf"
                        filename = clean_filename(raw_file_name)
                        save_path = save_dir / filename

                        if save_path.exists():
                            log_fn(f"📁  [스킵] {filename}")
                            continue
                            
                        if is_similar_file_exists(save_dir, filename, 0.95):
                            log_fn(f"📁  [유사 스킵(95%+)] {filename}")
                            continue

                        pdf_url = urljoin(base_url, pdf_href)
                        pdf_resp = session.get(pdf_url, timeout=30)
                        if pdf_resp.status_code == 200 and len(pdf_resp.content) > 1000:
                            with open(save_path, "wb") as f:
                                f.write(pdf_resp.content)
                            log_fn(f"✅  [성공] {filename}")
                            download_count += 1

                if not found_today:
                    break

                page += 1
            except Exception as e:
                log_fn(f"⚠️  네이버 {self.display_name} 수집 오류: {e}")
                break

        return download_count
