import pytest
from pathlib import Path
from datetime import datetime
from config import AppConfig
from ai_summary import generate_ai_summary_for_folder
from collectors import CollectorManager

def test_generate_ai_summary_for_folder(tmp_path: Path):
    target_dir = tmp_path / "20260729"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 가상의 리포트 파일 생성
    pdf_file = target_dir / "삼성전자_기업분석.pdf"
    pdf_file.write_text("Dummy PDF Content for Samsung Electronics")

    logs = []
    def logger(msg: str):
        logs.append(msg)

    result = generate_ai_summary_for_folder(target_dir, "20260729", gemini_api_key="", log_fn=logger)
    assert result != ""
    assert (target_dir / "AI_Report_Summary_20260729.md").exists()
    assert (target_dir / "AI_Report_Summary_20260729.txt").exists()
    assert any("AI 요약 저장 완료" in log for log in logs)

def test_collector_manager_feature_toggles(tmp_path: Path):
    mgr = CollectorManager()
    logs = []
    def logger(msg: str):
        logs.append(msg)

    # 1. 두 기능 모두 OFF인 경우
    config_none = AppConfig(save_dir=tmp_path, enable_report_download=False, enable_ai_summary=False)
    ret = mgr.run(config_none, logger)
    assert ret == 0
    assert any("하나도 선택되지 않았습니다" in log for log in logs)

    # 2. AI 요약만 ON인 경우 (기존 파일 요약만 동작)
    logs.clear()
    target_dir = tmp_path / datetime.now().strftime("%Y%m%d")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "테스트_리포트.pdf").write_text("Test Report PDF")

    config_ai = AppConfig(save_dir=tmp_path, enable_report_download=False, enable_ai_summary=True)
    mgr.run(config_ai, logger)
    assert any("AI 분석 요약: ✅ ON" in log for log in logs)
    assert (target_dir / f"AI_Report_Summary_{datetime.now().strftime('%Y%m%d')}.md").exists()
