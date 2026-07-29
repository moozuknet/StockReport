import pytest
from pathlib import Path
from datetime import datetime
from utils import clean_filename, format_date, is_similar_file_exists, parse_company_and_title

def test_clean_filename():
    assert clean_filename('리포트: 삼성전자/목표가? "10만"') == "리포트 삼성전자목표가 10만"
    assert clean_filename('   [특수문자]   테스트???   ') == "[특수문자] 테스트"
    assert clean_filename('정상_파일명.pdf') == "정상_파일명.pdf"

def test_format_date():
    dt = datetime(2026, 7, 29)
    formats = format_date(dt)
    assert formats['folder_name'] == '20260729'
    assert formats['naver_date'] == '26.07.29'
    assert formats['dot_date'] == '2026.07.29'
    assert formats['slash_date'] == '2026/07/29'

def test_parse_company_and_title():
    comp, title = parse_company_and_title("삼성전자 (005930) 3분기 실적 전망")
    assert comp == "삼성전자"
    assert title == "3분기 실적 전망"

    comp, title = parse_company_and_title("SK하이닉스 반도체 업황 분석")
    assert comp == ""
    assert title == "SK하이닉스 반도체 업황 분석"

def test_is_similar_file_exists(tmp_path: Path):
    (tmp_path / "[삼성전자] 3분기 실적 분석.pdf").touch()

    assert is_similar_file_exists(tmp_path, "[삼성전자] 3분기 실적 분석보고서.pdf", 0.80) is True
    assert is_similar_file_exists(tmp_path, "[현대차] 자동차 산업 전망.pdf", 0.95) is False
