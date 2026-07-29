import time
import pytest
from config import AppConfig
from scheduler import ReportScheduler

class MockCollectorManager:
    def __init__(self):
        self.called_count = 0

    def run(self, config, logger):
        self.called_count += 1
        logger(f"Mock collection executed #{self.called_count}")

def test_scheduler_single_run():
    config = AppConfig(interval_minutes=0) # 1회 실행
    logs = []
    def logger(msg):
        logs.append(msg)

    mock_mgr = MockCollectorManager()
    scheduler = ReportScheduler(config, logger, runner_fn=mock_mgr.run)
    
    scheduler.start()
    scheduler.join(timeout=2.0)

    assert mock_mgr.called_count == 1
    assert any("Mock collection executed #1" in log for log in logs)
    assert scheduler.is_running is False

def test_scheduler_stop():
    config = AppConfig(interval_minutes=1) # 1분 주기 반복
    logs = []
    def logger(msg):
        logs.append(msg)

    mock_mgr = MockCollectorManager()
    scheduler = ReportScheduler(config, logger, runner_fn=mock_mgr.run)
    
    scheduler.start()
    time.sleep(0.3)
    scheduler.stop()
    scheduler.join(timeout=2.0)

    assert mock_mgr.called_count >= 1
    assert scheduler.is_running is False
    assert any("수집 스케줄러가 중지되었습니다" in log for log in logs)
