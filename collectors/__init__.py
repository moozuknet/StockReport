import os
from pathlib import Path
from typing import List, Dict, Callable

# Playwright가 PyInstaller EXE 환경에서도 윈도우 사용자 폴더(%USERPROFILE%\AppData\Local\ms-playwright)를 절대경로로 참조하도록 설정
ms_playwright_path = Path.home() / "AppData" / "Local" / "ms-playwright"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ms_playwright_path)

from config import AppConfig, send_telegram_message
from collectors.base import BaseCollector
from collectors.kyobo import KyoboCollector
from collectors.mirae import MiraeCollector
from collectors.hankyung import HankyungCollector
from collectors.naver import NaverCollector, NAVER_CATEGORIES

class CollectorManager:
    def __init__(self):
        self.collectors: List[BaseCollector] = [
            KyoboCollector(),
            MiraeCollector(),
            HankyungCollector()
        ]
        for sub_url, config_key, display_name in NAVER_CATEGORIES:
            self.collectors.append(NaverCollector(sub_url, config_key, display_name))

    def get_active_collector_names(self, config: AppConfig) -> List[str]:
        return [c.name for c in self.collectors if config.selected_sites.get(c.config_key, False)]

    def run(self, config: AppConfig, log_fn: Callable[[str], None]) -> int:
        active_collectors = [c for c in self.collectors if config.selected_sites.get(c.config_key, False)]

        if not active_collectors:
            log_fn("⚠️ [경고] 선택된 수집 대상 사이트가 없습니다.")
            return 0

        target_dates = config.get_target_dates()
        total_downloaded = 0

        log_fn("🚀 ==========================================")
        log_fn(f"🚀 통합 증권 리포트 수집 시작 (총 {len(target_dates)}개 일자)")
        log_fn("🚀 ==========================================\n")

        for target_dt in target_dates:
            save_dir = config.get_effective_save_dir(target_dt)
            save_dir.mkdir(parents=True, exist_ok=True)
            date_str = target_dt.strftime("%Y-%m-%d")

            log_fn(f"📅 >>> [일자 수집 시작] {date_str} (📁 저장: {save_dir})")
            day_downloaded = 0

            for collector in active_collectors:
                try:
                    cnt = collector.fetch(save_dir, target_dt, log_fn)
                    day_downloaded += cnt
                except Exception as e:
                    log_fn(f"❌ [오류] {collector.name} ({date_str}) 수집 중 예외 발생: {e}\n")

            total_downloaded += day_downloaded
            log_fn(f"📊 <<< [{date_str} 수집 완료] 일자별 다운로드: {day_downloaded}개\n")

        log_fn("📊 ==========================================")
        log_fn(f"📊 [전체 작업 완료] 총 신규 다운로드: {total_downloaded}개")
        log_fn("📊 ==========================================\n")

        # 텔레그램 알림 전송 조건:
        # 1회 즉시 실행(interval_minutes == 0)일 때는 0개여도 메시지 전송
        # 주기적 반복 실행(interval_minutes > 0)일 때만 0개일 경우 전송 생략
        if config.telegram_enabled and config.telegram_token and config.telegram_chat_id:
            should_send = (config.interval_minutes == 0) or (total_downloaded > 0)
            
            if should_send:
                d_range_str = f"{target_dates[0].strftime('%Y-%m-%d')} ~ {target_dates[-1].strftime('%Y-%m-%d')}" if len(target_dates) > 1 else target_dates[0].strftime('%Y-%m-%d')
                
                tg_msg = (
                    f"<b>🤖 [증권 리포트 수집 완료 알림]</b>\n"
                    f"📅 <b>수집 일자:</b> {d_range_str}\n"
                    f"📁 <b>저장 경로:</b> {config.save_dir}\n"
                    f"📥 <b>신규 다운로드:</b> {total_downloaded}개\n"
                    f"⏱️ <b>동작 모드:</b> {'1회 즉시 실행' if config.interval_minutes == 0 else f'{config.interval_minutes}분 반복'}"
                )
                success, err_msg = send_telegram_message(config.telegram_token, config.telegram_chat_id, tg_msg)
                if success:
                    log_fn("📱 [텔레그램 알림] 전송 성공! ✅\n")
                else:
                    log_fn(f"📱 [텔레그램 알림] 전송 실패: {err_msg} ⚠️\n")
            else:
                log_fn("📱 [텔레그램 알림] 반복 수집 모드에서 신규 다운로드가 0개이므로 텔레그램 알림 전송을 생략합니다.\n")

        return total_downloaded
