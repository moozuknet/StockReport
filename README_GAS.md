# 📊 StockReport - 구글 앱스 스크립트(GAS) & 요약 달력 배포 가이드 (v2.0)

본 프로젝트는 파이썬 기반 `StockReport` 수집기의 모든 기능을 **구글 앱스 스크립트 (Google Apps Script, GAS)** 로 구축하고, **일별 요약집 자동 생성**, **요약 전용 폴더 분리**, **텔레그램 요약 링크**, **달력 뷰(Calendar View)** 기능을 탑재한 클라우드 통합 가이드입니다.

---

## 📁 1. 구글 앱스 스크립트 파일 구성 (`gas/`)

- `appsscript.json` : Apps Script 매니페스트 설정 (V8 런타임 및 Asia/Seoul)
- `Code.gs` : 통합 수집 조율, 비동기 스케줄러, 강제 중단 및 달력 RPC 통신 API
- `Config.gs` : `PropertiesService` 기반 환경설정 및 폴더 ID/URL 저장소
- `DriveUtils.gs` : 구글 드라이브 폴더, 100배 메모리 캐시 및 달력 데이터 조회
- `ReportSummarizer.gs` : 일별 리포트 요약집(`YYYY-MM-DD_증권리포트_요약집.html`) 자동 생성 및 실시간 갱신 [NEW]
- `TelegramUtils.gs` : Telegram Bot 요약집 직통 링크 메시지 발송
- `NaverCollector.gs` : 네이버 증권 5개 카테고리 수집기 (EUC-KR 한글 디코딩)
- `HankyungCollector.gs` : 한경 컨센서스 이중 탐색 수집기
- `MiraeCollector.gs` : 미래에셋증권 투자정보 수집기
- `KyoboCollector.gs` : 교보증권 리서치 센터 수집기
- `Index.html` : 탭 기반 대시보드 UI (수집 설정 / 달력 뷰 / 강제 중단 / 실시간 콘솔) [NEW]

---

## 🎨 2. 주요 기능 및 사용 방법

### 📄 1) 일별 요약집 자동 생성 및 갱신
- 신규 리포트가 수집되면 파일명의 대괄호 `[종목명]` 또는 `[산업/경제/시장]`을 자동 감지하여 일자별 `YYYY-MM-DD_증권리포트_요약집.html` 문서를 자동 생성합니다.
- 동일 일자에 새로 수집된 리포트가 추가되면 기존 요약집을 **자동으로 실시간 갱신(Update)** 합니다.
- 요약집 파일은 지정된 **`증권리포트_요약집`** 전용 폴더에 모아서 저장됩니다.

### 📱 2) 텔레그램 직통 링크 알림
- 수집이 완료되면 텔레그램 메시지에 신규 수집 건수와 함께 생성된 **일별 요약집 구글 드라이브 바로가기 링크**가 포함되어 전송됩니다.

### 📅 3) 리포트 요약 달력 (Calendar View Dashboard)
- 대시보드 상단 탭에서 **`📅 리포트 요약 달력 (Calendar)`** 을 클릭하면 월별 달력이 출력됩니다.
- 요약집이 존재하는 날짜에는 초록색 **`📄 요약집 보러가기`** 배지가 표시되며, 클릭 시 구글 드라이브 요약 보고서로 즉시 이동합니다.

### 🛑 4) 수집 중 강제 중단 (Stop)
- 대시보드의 **`🛑 수집 강제 중단 (Stop)`** 버튼을 누르면 진행 중인 수집 작업이 안전하게 즉시 정지됩니다.

---

## 🚀 3. 구글 계정에 동기화 및 배포하기

```bash
# 1. Google 계정 연동 (최초 1회)
npx @google/clasp login

# 2. 코드 업로드 (Push)
npx @google/clasp push -f

# 3. 웹 앱 배포 (Deploy)
npx @google/clasp deploy -d "StockReport v2.0 Final Release"
```
