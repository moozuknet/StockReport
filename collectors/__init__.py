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
from ai_summary import generate_ai_summary_for_folder

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
        if not config.enable_report_download and not config.enable_ai_summary:
            log_fn("⚠️ [경고] 실행할 기능(리포트 다운로드 또는 AI 분석 요약)이 하나도 선택되지 않았습니다.")
            return 0

        target_dates = config.get_target_dates()
        total_downloaded = 0
        ai_summaries: Dict[str, str] = {}

        log_fn("🚀 ==========================================")
        log_fn(f"🚀 증권 리포트 자동화 작업 시작 (총 {len(target_dates)}개 일자)")
        log_fn(f"📌 [기능 체크] 리포트 다운로드: {'✅ ON' if config.enable_report_download else '❌ OFF'} | AI 분석 요약: {'✅ ON' if config.enable_ai_summary else '❌ OFF'}")
        log_fn("🚀 ==========================================\n")

        # 1. 리포트 다운로드 수집 기능 (체크 시 실행)
        if config.enable_report_download:
            active_collectors = [c for c in self.collectors if config.selected_sites.get(c.config_key, False)]
            if not active_collectors:
                log_fn("⚠️ [경고] 선택된 수집 대상 사이트가 없습니다.")
            else:
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

        # 2. AI 분석 요약 기능 (체크 시 실행)
        if config.enable_ai_summary:
            for target_dt in target_dates:
                save_dir = config.get_effective_save_dir(target_dt)
                date_str = target_dt.strftime("%Y%m%d")
                summary_text = generate_ai_summary_for_folder(
                    save_dir=save_dir,
                    date_str=date_str,
                    gemini_api_key=config.gemini_api_key,
                    log_fn=log_fn
                )
                if summary_text:
                    ai_summaries[date_str] = summary_text

        log_fn("📊 ==========================================")
        log_fn(f"📊 [전체 작업 완료] 총 신규 다운로드: {total_downloaded}개 | 생성된 AI 요약: {len(ai_summaries)}개")
        log_fn("📊 ==========================================\n")

        # 텔레그램 알림 전송 로직
        if config.telegram_enabled and config.telegram_token and config.telegram_chat_id:
            should_send = (config.interval_minutes == 0) or (total_downloaded > 0) or (len(ai_summaries) > 0)
            
            if should_send:
                d_range_str = f"{target_dates[0].strftime('%Y-%m-%d')} ~ {target_dates[-1].strftime('%Y-%m-%d')}" if len(target_dates) > 1 else target_dates[0].strftime('%Y-%m-%d')
                
                msg_parts = [
                    f"<b>🤖 [증권 리포트 작업 완료 알림]</b>",
                    f"📅 <b>작업 일자:</b> {d_range_str}",
                    f"📁 <b>저장 경로:</b> {config.save_dir}"
                ]
                if config.enable_report_download:
                    msg_parts.append(f"📥 <b>신규 다운로드:</b> {total_downloaded}개")
                if config.enable_ai_summary and ai_summaries:
                    latest_summary = list(ai_summaries.values())[0]
                    # 텔레그램 메시지 길이 제한(4000자) 고려 요약 본문 일부 포함
                    summary_preview = latest_summary[:1200]
                    msg_parts.append(f"\n<b>📝 [AI 리포트 요약 미리보기]</b>\n{summary_preview}")

                msg_parts.append(f"\n⏱️ <b>동작 모드:</b> {'1회 즉시 실행' if config.interval_minutes == 0 else f'{config.interval_minutes}분 반복'}")
                
                tg_msg = "\n".join(msg_parts)
                success, err_msg = send_telegram_message(config.telegram_token, config.telegram_chat_id, tg_msg)
                if success:
                    log_fn("📱 [텔레그램 알림] 전송 성공! ✅\n")
                else:
                    log_fn(f"📱 [텔레그램 알림] 전송 실패: {err_msg} ⚠️\n")
            else:
                log_fn("📱 [텔레그램 알림] 반복 수집 모드에서 신규 다운로드/AI 요약 변화가 없으므로 알림을 생략합니다.\n")

        return total_downloaded

