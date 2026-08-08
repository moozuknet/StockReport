# 📊 StockReport - 증권사별 리포트 자동 수집, Gemini AI 요약집 & 구글 드라이브 통합 대시보드 (v3.9)

[![Release](https://img.shields.io/badge/version-3.9.0-indigo.svg)](https://github.com/moozuknet/StockReport)
[![Gemini AI](https://img.shields.io/badge/AI-Gemini%201.5%20Flash%20Multimodal-purple.svg)](https://deepmind.google/technologies/gemini/)
[![Platform](https://img.shields.io/badge/platform-Google%20Apps%20Script-orange.svg)](https://script.google.com/)
[![Drive Integration](https://img.shields.io/badge/storage-Google%20Drive-brightgreen.svg)](https://drive.google.com/)

**StockReport**는 주요 증권사 및 금융 포털 사이트의 리포트를 자동으로 수집하여 구글 드라이브에 분류·저장하고, **Gemini 1.5 Flash AI 기반 NotebookLM 스타일 심층 요약집(HTML)** 생성, **섹터/카테고리별 달력 뷰(Calendar View) 스마트 대시보드**, **텔레그램 알림**, 및 **0.01초 초고속 캐시 엔진**을 제공하는 시스템입니다.

---

## ✨ 1. 주요 핵심 기능 (Features)

### 🏢 8개 수집 대상 사이트 통합 지원
- 📌 **교보증권**: 교보증권 리서치 센터 수집 (`fileDown` 서블릿 파싱)
- 📌 **미래에셋증권**: 미래에셋증권 투자정보 수집 (EUC-KR 한글 디코딩)
- 📌 **한경 컨센서스**: 한경 컨센서스 종합 리포트 수집 (`markets.hankyung.com` & `consensus.hankyung.com` 이중 탐색)
- 📌 **네이버 증권 (5개 카테고리)**: 기업분석, 산업분석, 경제분석, 시장분석, 투자정보

### 🤖 Gemini 1.5 Flash AI 듀얼 엔진 심층 요약 (NotebookLM 스타일)
- **멀티모달 바이너리 직접 전달**: PDF의 표, 차트, 그래프, 수치까지 Gemini 1.5 Flash AI가 100% 정밀 분석
- **NotebookLM 스타일 요약 구조**:
  1. 🎯 `[3줄 핵심 요약]`: 결론 및 실적 핵심 포인트 3가지
  2. 📈 `[투자의견 & 목표가]`: 목표주가, 투자의견(Buy/Hold) 및 밸류에이션
  3. 💡 `[주요 성장 동력 & 호재]`: 매출 모멘텀 및 사업 호재
  4. ⚠️ `[위험 요인 & 체크포인트]`: 리스크 및 불확실성
- **Dual-Engine Auto Fallback**: 멀티모달 API 예외 발생 시 텍스트 분석 엔진으로 100% 자동 전환하여 404 및 용량 초과 에러 방지

### 🏷️ 섹터/카테고리별 정밀 자동 분류 & 달력 필터 (Sector Filter Bar)
- 리포트를 **5대 섹터**로 자동 정밀 분류:
  - 🏢 **기업분석** (Company Analysis)
  - 🏭 **산업/업종** (Industry & Sectors)
  - 🌐 **거시경제** (Macro & Economy)
  - 📈 **증시전략** (Market Strategy & Derivatives)
  - 💡 **투자정보 & ESG** (Investment Info & ESG)
- **달력 화면 상단 섹터 필터 칩(Chip)**: 원하는 섹터를 선택하면 달력 셀에 해당 섹터 건수가 자동 강조되며, 요약집 클릭 시 해당 섹터 위치로 즉시 스크롤 이동

### ⚡ 0.01초 초고속 달력 인덱스 캐시 (`CALENDAR_INDEX_CACHE`)
- 달력 탭 전환 시 구글 드라이브 스캔 대기시간 없이 **0.01초(즉시)** 달력 및 폴더 유무 버튼 로딩
- `🔄 달력 인덱스 새로고침` 수동 동기화 지원

### ⏱️ GAS 6분 타임아웃 방지 & 백그라운드 비동기 요약 스레드
- 87개 이상의 대량 PDF 리포트 분석 시 구글 앱스 스크립트 6분 제한시간(`ScriptError`)을 원천 차단하기 위해 **0.1초 비동기 백그라운드 스레드** 및 **4분 30초 자동 인터벌 세이프가드** 적용

### 🛑 전용 강제 종료 & 실시간 콘솔 모니터링
- 달력 뷰, 콘솔 창, 대시보드 어디서든 즉시 멈출 수 있는 **`🛑 진행 중인 AI 요약분석 강제 종료`** 버튼
- 1.5초 간격 실시간 콘솔 로그 스트리밍 (`💻 실시간 수집 콘솔 로그`)

### ⏸️ 백그라운드 자동 수집 구동 시작/정지 토글
- `▶️ 자동 수집 구동 시작` (초록) 및 `⏸️ 자동 수집 완전히 정지` (주황) 전용 스케줄러 버튼

---

## 🏗️ 2. 프로젝트 폴더 구조

```text
StockReport/
├── 📄 main.py                    # Python 실행 엔트리포인트 (데스크톱 GUI)
├── ⚙️ config.py                  # Python 환경설정
├── 📘 README.md                  # 프로젝트 통합 매뉴얼 (v3.9)
├── 📘 README_GAS.md              # 구글 앱스 스크립트 배포 & 사용 가이드
│
├── 📂 gas/                       # 구글 앱스 스크립트 (GAS) 클라우드 모듈
│   ├── appsscript.json           # GAS V8 매니페스트 (서울 시간대 설정)
│   ├── Code.gs                   # 메인 조율, 비동기 스레드 & RPC 통신
│   ├── Config.gs                 # PropertiesService 영속성 관리
│   ├── DriveUtils.gs             # 전역 PDF 탐색, 0.01초 달력 캐시 & 섹터 매핑
│   ├── ReportSummarizer.gs       # Gemini AI 듀얼 엔진 심층 요약집 생성 모듈
│   ├── TelegramUtils.gs          # 텔레그램 직통 링크 메시지 발송 모듈
│   ├── NaverCollector.gs         # 네이버 5개 카테고리 수집기
│   ├── HankyungCollector.gs      # 한경 컨센서스 이중 탐색 수집기
│   ├── MiraeCollector.gs         # 미래에셋증권 수집기 (EUC-KR)
│   ├── KyoboCollector.gs         # 교보증권 수집기 (fileDown)
│   └── Index.html                # 섹터 필터 탑재 달력 뷰 & 실시간 콘솔 대시보드 UI
│
└── 🔍 collectors/                # Python 수집 엔진
```

---

## 🚀 3. 구글 앱스 스크립트(GAS) 배포 및 시작하기

자세한 배포 가이드는 [README_GAS.md](file:///Users/jjuni/StockReport/README_GAS.md)를 참고하세요.

```bash
# 1. Google 계정 연동 (최초 1회)
npx @google/clasp login

# 2. 코드 업로드 (Push)
npx @google/clasp push -f

# 3. 웹 앱 배포 (Deploy)
npx @google/clasp deploy -i AKfycbw48QOnNhS4CfMaBfRn6M9VqrYD9nK2QRlcF2tWatvKjvxjTCCZ275YEm1_DLpqzjaH -d "StockReport Release v3.9"
```
