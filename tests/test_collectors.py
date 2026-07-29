import pytest
from pathlib import Path
from datetime import datetime
from config import AppConfig
from collectors import CollectorManager

def test_collector_manager_selected_sites():
    config = AppConfig()
    config.selected_sites["교보증권"] = False
    config.selected_sites["미래에셋증권"] = True

    mgr = CollectorManager()
    active_names = mgr.get_active_collector_names(config)
    
    assert "교보증권" not in active_names
    assert "미래에셋증권" in active_names
