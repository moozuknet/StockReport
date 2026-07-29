# 📊 StockReport - 증권사별 리포트 자동 수집기 (v1.0.0)

[![Release](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/moozuknet/StockReport)
[![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt5-orange.svg)](https://pypi.org/project/PyQt5/)
[![Scraper](https://img.shields.io/badge/automation-Playwright-red.svg)](https://playwright.dev/python/)

**StockReport**는 주요 증권사 및 금융 포털 사이트의 리포트를 자동으로 수집하여 날짜별 폴더에 PDF 파일로 정리해 주는 파이썬 기반의 모던 데스크톱 애플리케이션입니다.

---

## 🚀 1. 프로젝트 개요 (Overview)

매일 쏟아지는 증권사 종목 리포트, 산업 분석, 경제/시장 동향 PDF 파일을 수동으로 다운로드받는 번거로움을 해결하기 위해 개발되었습니다.  
Playwright 기반의 자동화 엔진과 PyQt5 DirectWrite 엔진을 탑재하여 세금계산서 자동정리 프로그램과 100% 동일한 선명한 원색 이모지 콘솔과 모던 UI 경험을 제공합니다.

---

## ✨ 2. 주요 기능 분석 (Feature Breakdown)

### 🏢 8개 수집 대상 사이트 통합 지원
- 📌 **교보증권**: 교보증권 리서치 센터 수집 (Playwright 크롬 엔진)
- 📌 **미래에셋증권**: 미래에셋증권 투자정보 수집 (Playwright & BeautifulSoup)
- 📌 **한경 컨센서스**: 한경 컨센서스 종합 리포트 수집 (Playwright & BeautifulSoup)
- 📌 **네이버 증권 (5개 카테고리)**:
  - 🔍 네이버 기업분석
  - 🔍 네이버 산업분석
  - 🔍 네이버 경제분석
  - 🔍 네이버 시장분석
  - 🔍 네이버 투자정보

### 📅 스마트 날짜 모드
- ☀️ **당일 (오늘)**: 오늘 날짜의 신규 등록 리포트 수집
- 📆 **특정 날짜 수집**: 지정한 단일 일자의 리포트 과거 이력 수집
- 🗓️ **날짜 구간 수집**: 시작일부터 종료일까지의 구간을 자동 순회 수집

### ⏱️ 스케줄러 & 동작 주기 설정
- ⚡ **즉시 실행 (1회만)**: 1회 수집 완료 후 자동으로 수집 버튼이 재활성화되고 중지 버튼이 비활성화되는 스레드 안심 자동 복원
- 🔄 **반복 자동 수집**: 10분, 30분, 1시간, 2시간, 3시간, 6시간, 12시간, 24시간 간격 주기적 백그라운드 수집

### 📱 스마트 텔레그램 알림 (Message Filtering)
- 1회 즉시 실행 시: 신규 다운로드 파일이 0개여도 수집 결과 메시지 전송
- 주기적 반복 수집 시: **신규 다운로드 파일이 1개 이상일 때만 알림 전송** (0개일 경우 알림 생략으로 피로도 방지)

### 🎨 PyQt5 DirectWrite 모던 UI
- 윈도우 최신 DirectWrite 엔진 탑재로 노란 폴더(`📁`), 핑크 핀(`📌`), 초록 체크(`✅`), 폰(`📱`), 로켓(`🚀`) 등 **100% 원색 멀티컬러 비트맵 이모지** 출력
- 4열 넓은 그리드 배치, 120% 정갈한 로그 행간, 52px 대형 수집 시작/중지 버튼 적용
- 주식 차트 컨셉의 누끼 투명 배경 커스텀 아이콘 (`app_icon.png` / `app_icon.ico`) 탑재

---

## 🏗️ 3. 시스템 아키텍처 및 폴더 구조 (Architecture & Directory Tree)

```text
StockReport/
├── 📄 main.py                    # 애플리케이션 메인 실행 엔트리 포인트
├── ⚙️ config.py                  # AppConfig 데이터클래스, StockReport.json 영속성 및 텔레그램 연동
├── ⏱️ scheduler.py               # 백그라운드 수집 스케줄러 & 1회성 종료 콜백
├── 📄 StockReport.json           # 사용자 환경 설정 자동 저장 파일
├── 🖼️ app_icon.png / app_icon.ico # 투명 배경 커스텀 리서치 아이콘
├── 📜 run.bat                    # 파이썬 실행 전용 배치 스크립트
├── 📘 README.md                  # 프로젝트 매뉴얼 문서 (v1.0.0)
│
├── 🎨 ui/                        # PyQt5 GUI 레이어
│   └── app_qt.py              # 모던 데스크톱 UI 및 DirectWrite 실시간 콘솔
│
├── 🔍 collectors/                # 증권사별 리포트 수집 엔진 모듈
│   ├── __init__.py            # CollectorManager (수집 조율 및 텔레그램 스마트 알림)
│   ├── base.py                # BaseCollector (공통 추상 클래스 및 ms-playwright 경로 바인딩)
│   ├── kyobo.py               # 교보증권 수집기 (Playwright)
│   ├── mirae.py               # 미래에셋증권 수집기 (Playwright & BeautifulSoup)
│   ├── hankyung.py            # 한경 컨센서스 수집기 (Playwright & BeautifulSoup)
│   └── naver.py               # 네이버 증권 5개 카테고리 수집기 (Requests & BeautifulSoup)
│
├── 🧪 tests/                     # Automated Test Suite (pytest)
│   ├── test_collectors.py     # 수집기 단위 테스트
│   ├── test_config.py         # JSON 설정 저장/로드 테스트
│   ├── test_scheduler.py      # 스케줄러 작동 테스트
│   └── test_utils.py          # 유틸리티 함수 테스트
│
└── 📦 dist/                      # PyInstaller 빌드 결과물
    └── StockReport/
        └── StockReport.exe    # 윈도우 무설치 실행 파일
```

---

## 💻 4. 설치 및 사용 방법 (Installation & Usage)

### 1) 파이썬 환경 구축 (소스코드 실행)

파이썬 3.10 이상 환경에서 의존성 라이브러리를 설치합니다.

```bash
# 의존성 패키지 설치
pip install PyQt5 playwright requests beautifulsoup4 pytest pyinstaller

# Playwright 크롬 브라우저 드라이버 설치
playwright install chromium
```

### 2) 소스코드 실행

```bash
# 메인 파일 실행
python main.py

# 또는 배치 스크립트 실행
run.bat
```

---

## 🛠️ 5. EXE 실행 파일 빌드 방법 (PyInstaller Build)

PyInstaller를 이용하여 독립형 윈도우 실행 파일(`StockReport.exe`)로 패키징합니다.

```bash
py -3.13 -m PyInstaller --noconfirm --onedir --windowed --icon=app_icon.ico --add-data "app_icon.png;." --add-data "app_icon.ico;." --name StockReport main.py
```

- **빌드 결과물 위치**: `dist/StockReport/StockReport.exe`
- 생성된 `dist/StockReport` 폴더 전체를 배포하거나 `StockReport.exe`를 실행하시면 파이썬 환경이 없는 윈도우 PC에서도 즉시 구동됩니다.

---

## ⚙️ 6. 설정 파일 규격 (`StockReport.json`)

`StockReport.json` 파일은 프로그램 동작 시 환경설정을 자동 저장 및 복원합니다.

```json
{
  "save_dir": "G:\\내 드라이브\\주식\\증권사별리포트",
  "use_date_folder": true,
  "interval_minutes": 0,
  "selected_sites": {
    "교보증권": true,
    "미래에셋증권": true,
    "한경 컨센서스": true,
    "네이버_기업분석": true,
    "네이버_산업분석": true,
    "네이버_경제분석": true,
    "네이버_시장분석": true,
    "네이버_투자정보": true
  },
  "date_mode": "today",
  "single_date": "2026-07-29",
  "start_date": "2026-07-29",
  "end_date": "2026-07-29",
  "telegram_enabled": true,
  "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "telegram_chat_id": "YOUR_TELEGRAM_CHAT_ID"
}
```

---

## 🧪 7. 자동화 테스트 실행 (Testing)

```bash
py -3.13 -m pytest tests/
```

모든 단위 테스트(8개)가 100% 통과하도록 검증되었습니다.

---

## 🏷️ 8. 버전 및 라이선스 (Release Note)

- **Current Version**: `v1.0.0`
- **Repository**: [https://github.com/moozuknet/StockReport](https://github.com/moozuknet/StockReport)
- **Developer**: moozuknet
