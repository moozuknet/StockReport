import json
import pytest
from pathlib import Path
from datetime import datetime, date
from config import AppConfig

def test_app_config_json_save_load(tmp_path: Path):
    json_file = tmp_path / "test_settings.json"
    
    config = AppConfig()
    config.save_dir = Path("/custom/save/dir")
    config.use_date_folder = False
    config.interval_minutes = 30
    config.selected_sites["교보증권"] = False
    config.selected_sites["미래에셋증권"] = True
    config.date_mode = "single"
    config.single_date = date(2026, 7, 25)
    config.enable_report_download = True
    config.enable_ai_summary = False
    config.gemini_api_key = "AIzaSyTestKey123"
    config.telegram_enabled = True
    config.telegram_token = "123456:ABC-DEF"
    config.telegram_chat_id = "987654321"

    config.save_to_json(json_file)
    assert json_file.exists()

    loaded_config = AppConfig.load_from_json(json_file)
    assert loaded_config.save_dir == Path("/custom/save/dir")
    assert loaded_config.use_date_folder is False
    assert loaded_config.interval_minutes == 30
    assert loaded_config.selected_sites["교보증권"] is False
    assert loaded_config.selected_sites["미래에셋증권"] is True
    assert loaded_config.date_mode == "single"
    assert loaded_config.single_date == date(2026, 7, 25)
    assert loaded_config.enable_report_download is True
    assert loaded_config.enable_ai_summary is False
    assert loaded_config.gemini_api_key == "AIzaSyTestKey123"
    assert loaded_config.telegram_enabled is True
    assert loaded_config.telegram_token == "123456:ABC-DEF"
    assert loaded_config.telegram_chat_id == "987654321"

