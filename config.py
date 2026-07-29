import json
import requests
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Union, Tuple

APP_VERSION = "1.0.0"

SITE_KEYS: List[str] = [
    "교보증권",
    "미래에셋증권",
    "한경 컨센서스",
    "네이버_기업분석",
    "네이버_산업분석",
    "네이버_경제분석",
    "네이버_시장분석",
    "네이버_투자정보"
]

@dataclass
class AppConfig:
    save_dir: Path = field(default_factory=lambda: Path.home() / "Downloads")
    use_date_folder: bool = True
    interval_minutes: int = 0  # 0: 1회 즉시 실행, >0: 주기 반복 (분 단위)
    selected_sites: Dict[str, bool] = field(default_factory=lambda: {key: True for key in SITE_KEYS})
    
    # 날짜 수집 옵션: "today" (당일), "single" (단일 날짜), "range" (구간 수집)
    date_mode: str = "today"
    single_date: Union[date, datetime] = field(default_factory=lambda: datetime.now().date())
    start_date: Union[date, datetime] = field(default_factory=lambda: datetime.now().date())
    end_date: Union[date, datetime] = field(default_factory=lambda: datetime.now().date())

    # 텔레그램 알림 설정
    telegram_enabled: bool = False
    telegram_token: str = ""
    telegram_chat_id: str = ""

    def get_effective_save_dir(self, dt: Union[date, datetime] = None) -> Path:
        """날짜 하위 폴더 사용 여부에 따른 실제 저장 경로를 반환합니다."""
        if dt is None:
            dt = datetime.now()
        
        if self.use_date_folder:
            folder_name = dt.strftime("%Y%m%d")
            return self.save_dir / folder_name
        return self.save_dir

    def get_target_dates(self) -> List[datetime]:
        """설정된 날짜 모드에 따라 수집할 datetime 객체 목록을 반환합니다."""
        now = datetime.now()
        
        if self.date_mode == "single":
            d = self.single_date
            if isinstance(d, str):
                d = datetime.strptime(d, "%Y-%m-%d").date()
            dt = datetime(d.year, d.month, d.day)
            return [dt]
        elif self.date_mode == "range":
            d_start = self.start_date
            d_end = self.end_date

            if isinstance(d_start, str):
                d_start = datetime.strptime(d_start, "%Y-%m-%d").date()
            if isinstance(d_end, str):
                d_end = datetime.strptime(d_end, "%Y-%m-%d").date()

            if d_start > d_end:
                d_start, d_end = d_end, d_start

            result = []
            curr = d_start
            while curr <= d_end:
                result.append(datetime(curr.year, curr.month, curr.day))
                curr += timedelta(days=1)
            return result
        else:
            # "today"
            return [datetime(now.year, now.month, now.day)]

    def save_to_json(self, filepath: Path = Path("StockReport.json")):
        """설정값을 JSON 파일로 저장합니다."""
        data = {
            "save_dir": str(self.save_dir),
            "use_date_folder": self.use_date_folder,
            "interval_minutes": self.interval_minutes,
            "selected_sites": self.selected_sites,
            "date_mode": self.date_mode,
            "single_date": self.single_date.strftime("%Y-%m-%d") if isinstance(self.single_date, (date, datetime)) else str(self.single_date),
            "start_date": self.start_date.strftime("%Y-%m-%d") if isinstance(self.start_date, (date, datetime)) else str(self.start_date),
            "end_date": self.end_date.strftime("%Y-%m-%d") if isinstance(self.end_date, (date, datetime)) else str(self.end_date),
            "telegram_enabled": self.telegram_enabled,
            "telegram_token": self.telegram_token,
            "telegram_chat_id": self.telegram_chat_id
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, filepath: Path = Path("StockReport.json")) -> 'AppConfig':
        """JSON 파일에서 설정값을 로드합니다. 파일이 없을 경우 기본값을 반환합니다."""
        config = cls()
        target_path = filepath
        if not target_path.exists():
            legacy_path = Path("settings.json")
            if legacy_path.exists():
                target_path = legacy_path

        if not target_path.exists():
            return config

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "save_dir" in data:
                config.save_dir = Path(data["save_dir"])
            if "use_date_folder" in data:
                config.use_date_folder = data["use_date_folder"]
            if "interval_minutes" in data:
                config.interval_minutes = data["interval_minutes"]
            if "selected_sites" in data:
                config.selected_sites.update(data["selected_sites"])
            if "date_mode" in data:
                config.date_mode = data["date_mode"]

            if "single_date" in data:
                config.single_date = datetime.strptime(data["single_date"], "%Y-%m-%d").date()
            if "start_date" in data:
                config.start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            if "end_date" in data:
                config.end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()

            if "telegram_enabled" in data:
                config.telegram_enabled = data["telegram_enabled"]
            if "telegram_token" in data:
                config.telegram_token = data["telegram_token"]
            if "telegram_chat_id" in data:
                config.telegram_chat_id = data["telegram_chat_id"]

        except Exception as e:
            print(f"[설정 로드 오류] {e}")

        return config

def send_telegram_message(token: str, chat_id: str, message: str) -> Tuple[bool, str]:
    """텔레그램 메시지를 전송하고 성공 여부를 반환합니다."""
    if not token or not chat_id:
        return False, "봇 토큰과 챗 ID를 입력해주세요."
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        res_data = resp.json()
        if resp.status_code == 200 and res_data.get("ok"):
            return True, "메시지 전송 성공!"
        else:
            err_desc = res_data.get("description", "알 수 없는 오류")
            return False, f"텔레그램 전송 실패: {err_desc}"
    except Exception as e:
        return False, f"텔레그램 통신 예외: {e}"
