/**
 * Config.gs - StockReport 수집기 환경설정 관리 모듈
 * PropertiesService.getUserProperties()를 활용한 영속성 관리
 */

var CONFIG_KEY = "STOCK_REPORT_CONFIG";

function getDefaultConfig() {
  var todayStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd");
  return {
    save_folder_name: "증권사별리포트",
    save_folder_id: "",
    summary_folder_name: "증권리포트_요약집",
    summary_folder_id: "",
    gemini_api_key: "",
    gemini_model: "gemini-flash-latest",
    custom_prompt: "당신은 기관 투자자 대상의 글로벌 자산운용사 시니어 에쿼티 애널리스트이자 리스크 관리 전문가입니다. 제공된 복수의 기업 분석 및 산업 리포트 텍스트와 하단의 자산 배분 기준을 바탕으로, 파일 제목에 명시된 `[종목 또는 카테고리명]` 분류 기준에 따른 유기적인 크로스 분석 요약, 펀더멘털 비교 테이블, 리스크 평가 및 매크로 스트레스 테스트 수치 시뮬레이션이 모두 포함된 종합 보고서를 작성해 주세요.\n\n" +
      "[분석 및 작성 지침]\n" +
      "1. 종목/카테고리별 그룹화 및 내러티브: 각 리포트 내용이 어떤 [종목/카테고리]에 속하는지 명확히 분류하고, 단편적인 수치 나열을 지양하세요. 전방 산업의 변화, 공급망(BOM) 효율화, 신규 수주 및 신사업 확장성 등 중장기 성장 내러티브와 주요 재무/추정 지표(매출, 영업이익, 목표주가 변동 등)를 유기적으로 결합하여 작성하세요.\n" +
      "2. 모니터링 필수 체크리스트: 실적 턴어라운드 시점, 파이프라인 데이터 공개 일정, 락업 해제, 정책 예산 반영 등 주가 모멘텀 스케줄을 단기(3~6개월) 및 중장기 관점으로 구체적인 날짜와 일정 중심으로 도출하세요.\n" +
      "3. 다차원 리스크 분석: 일회성 비용에 따른 마진 희석, 매크로 변수(금리/환율), 경쟁 심화 및 전방 수요 둔화 가능성, 기술이전 공백 등 단기 및 중장기 리스크의 상충 관계(Trade-off)를 날카롭게 파악하여 인용구(>) 서식으로 작성하세요.\n" +
      "4. 섹터별 펀더멘털 비교 테이블 추가: 보고서 본문에 분석된 주요 기업들의 2Q26 OPM(%), ROE(%), 밸류에이션 특성(P/B, P/E 수준 및 낙폭 수준), 핵심 모멘텀/리스크 요인을 한눈에 파악할 수 있는 정밀한 마크다운(Markdown) 테이블을 반드시 포함해 주세요.\n" +
      "5. 매크로 시나리오 스트레스 테스트 수치 시뮬레이션 추가: 글로벌 매크로 충격(예: 원/달러 환율 1,450원 돌파 및 고착화, 하이퍼스케일러 CAPEX 우려에 따른 기술주 변동성 VXN 급등, 국내 증시 디레버리징 심화)을 가정한 스트레스 테스트 섹션을 신설하고, 제안된 4대 자산군(글로벌 배당귀족 커버드콜 35%, 저변동성 우량 인컴 25%, 국내 낙폭과대 알파/밸류업 25%, 현금성 안전자산 15%) 포트폴리오의 각 시나리오별 예상 자산가치 변동률(%) 및 헤지 메커니즘을 구체적인 추정 수치 스케줄로 정밀하게 구성해 주세요.\n" +
      "6. 시각적 계층 구조화 및 출력 서식: Markdown 헤더(##, ###)와 인용구(>)를 활용하여 가독성을 극대화하고, 대화형 텍스트나 로봇 같은 filler 표현을 배제한 완결된 보고서 형태로 출력해 주세요. 이 문서는 바로 Google Docs(문서)로 내보낼 수 있도록 정밀하게 격식에 맞춰 작성되어야 합니다.\n" +
      "7. 참조 소스(출처) 명시: 보고서 최하단에 본 분석에 활용된 모든 구글 드라이브 문서의 정확한 [파일 제목]과 해당 문서로 직접 이동할 수 있는 [원본 URL 링크]를 목록 형태로 명확히 작성해 주세요. (형식: `- [파일 제목](구글 드라이브 문서 URL)`)\n\n" +
      "[출력 형식]\n" +
      "## 1. 개별 종목 및 카테고리별 종합 분석\n" +
      "### ■ 종목/카테고리명: [예: 대우건설]\n" +
      "* **핵심 내러티브 및 모멘텀 요약**: ...\n" +
      "* **주요 재무 및 추정 지표**: ...\n\n" +
      "## 2. 국내외 주요 섹터별 펀더멘털 및 밸류에이션 비교 테이블\n\n" +
      "## 3. 향후 모니터링 필수 체크리스트 (시간별/이벤트별)\n" +
      "* **단기 핵심 이벤트 (3~6개월 내)**: (날짜 및 일정 중심 기술)\n" +
      "* **중장기 펀더멘털 확인 지표**: ...\n\n" +
      "## 4. 핵심 리스크 및 상충 관계 분석\n" +
      "> **[⚠️ 위험 요인 1: 단기 비용 부담 vs 중장기 효율화의 괴리]**\n" +
      "> **[⚠️ 위험 요인 2: 전방 시장 수요 압박 및 대외 변수]**\n" +
      "> **[⚠️ 위험 요인 3: 시장 기대치(컨센서스) 미달 및 멀티플 할인 요인]**\n\n" +
      "## 5. 매크로 시나리오 스트레스 테스트 수치 시뮬레이션\n\n" +
      "## 6. 참고 문헌 및 출처 (Source Files)\n" +
      "* 본 보고서 작성에 참고한 구글 드라이브 원본 리포트 목록:\n" +
      "  - [파일 제목 1](구글 드라이브 URL 1)\n",
    use_date_folder: true,
    interval_minutes: 0,
    selected_sites: {
      "교보증권": true,
      "미래에셋증권": true,
      "한경 컨센서스": true,
      "네이버_기업분석": true,
      "네이버_산업분석": true,
      "네이버_경제분석": true,
      "네이버_시장분석": true,
      "네이버_투자정보": true
    },
    date_mode: "today",
    single_date: todayStr,
    start_date: todayStr,
    end_date: todayStr,
    telegram_enabled: true,
    telegram_token: "",
    telegram_chat_id: ""
  };
}

function getConfig() {
  var props = PropertiesService.getUserProperties();
  var raw = props.getProperty(CONFIG_KEY);
  var defaults = getDefaultConfig();

  if (!raw) {
    saveConfig(defaults);
    return defaults;
  }
  try {
    var parsed = JSON.parse(raw);
    for (var k in defaults) {
      if (parsed[k] === undefined) {
        parsed[k] = defaults[k];
      }
    }
    return parsed;
  } catch (e) {
    saveConfig(defaults);
    return defaults;
  }
}

function saveConfig(config) {
  var props = PropertiesService.getUserProperties();
  props.setProperty(CONFIG_KEY, JSON.stringify(config));
  return config;
}

function getTargetDates(config) {
  var dates = [];

  if (config.date_mode === "single" && config.single_date) {
    var d = parseDateString(config.single_date);
    if (d) dates.push(d);
  } else if (config.date_mode === "range" && config.start_date && config.end_date) {
    var startD = parseDateString(config.start_date);
    var endD = parseDateString(config.end_date);
    if (startD && endD) {
      var curr = new Date(startD.getTime());
      while (curr <= endD) {
        dates.push(new Date(curr.getTime()));
        curr.setDate(curr.getDate() + 1);
      }
    }
  }

  if (dates.length === 0) {
    dates.push(new Date());
  }

  return dates;
}

function parseDateString(dateStr) {
  if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return null;
  var parts = dateStr.split("-");
  return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
}
