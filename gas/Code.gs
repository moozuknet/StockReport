/**
 * Code.gs - Google Apps Script 메인 실행 엔트리포인트 및 Web App 통신
 */

var currentLogs = [];

function doGet(e) {
  return HtmlService.createTemplateFromFile("Index")
    .evaluate()
    .setTitle("📊 StockReport - 증권사별 리포트 자동 수집기 & 요약 달력")
    .addMetaTag("viewport", "width=device-width, initial-scale=1.0");
}

function logMessage(msg) {
  Logger.log(msg);
  currentLogs.push(msg);
  saveRecentLogs(currentLogs);
}

/**
 * 수집기 통합 실행 함수
 */
function runStockReport(isScheduled) {
  if (isScheduled === undefined) isScheduled = false;

  currentLogs = [];
  setRunningFlag(true);
  clearStopRequested();

  try {
    var config = getConfig();
    var enableDownload = config.enable_report_download !== false;
    var enableAiSummary = config.enable_ai_summary !== false;

    if (!enableDownload && !enableAiSummary) {
      logMessage("⚠️ [경고] 실행할 기능(리포트 다운로드 수집 또는 AI 분석 요약)이 하나도 선택되지 않았습니다.");
      return { count: 0, logs: currentLogs };
    }

    var startTime = new Date().getTime();
    var maxTimeMs = 280 * 1000; // 4분 40초 안전 한계 (구글 서버 6분 타임아웃 방지)
    var timeLimitReached = false;

    var activeCollectors = enableDownload ? getActiveCollectors(config) : [];
    var targetDates = getTargetDates(config);
    var totalDownloaded = 0;
    var stoppedEarly = false;
    var latestSummaryInfo = null;

    logMessage("🚀 ==========================================");
    logMessage("🚀 증권 리포트 자동화 작업 시작 (총 " + targetDates.length + "개 일자)");
    logMessage("📌 [기능 체크] 리포트 다운로드: " + (enableDownload ? "✅ ON" : "❌ OFF") + " | AI 분석 요약: " + (enableAiSummary ? "✅ ON" : "❌ OFF"));
    logMessage("🚀 ==========================================\n");

    for (var d = 0; d < targetDates.length; d++) {
      if (isStopRequested()) {
        logMessage("🛑 [중단 요청 감지] 수집 작업이 강제 중단되었습니다.");
        stoppedEarly = true;
        break;
      }

      if (new Date().getTime() - startTime > maxTimeMs) {
        logMessage("⚠️ [구글 서버 실행 시간제한(4분 40초) 감지] 구글 스크립트 6분 자동 강제종료 타임아웃을 방지하기 위해 현재까지의 수집 내역(총 " + totalDownloaded + "개 다운로드)을 안전하게 저장하고 마무리합니다.");
        timeLimitReached = true;
        stoppedEarly = true;
        break;
      }

      var targetDt = targetDates[d];
      var saveFolder = getSaveFolderProxy(config, targetDt);
      var dateStr = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy-MM-dd");

      var dayDownloaded = 0;
      var downloadedReportTitles = [];
      var collectorLogFn = function(msg) {
        logMessage(msg);
        if (msg && msg.indexOf("✅ [성공]") !== -1) {
          var titleStr = msg.replace("✅ [성공]", "").trim();
          if (titleStr && downloadedReportTitles.indexOf(titleStr) === -1) {
            downloadedReportTitles.push(titleStr);
          }
        }
      };

      // 1. 리포트 다운로드 수집 기능 (체크 시 실행)
      if (enableDownload) {
        if (activeCollectors.length === 0) {
          logMessage("⚠️ [경고] 선택된 수집 대상 사이트가 없습니다.");
        } else {
          logMessage("📅 >>> [일자 수집 시작] " + dateStr + " (📁 구글드라이브 저장: " + saveFolder.getName() + ")");
          logMessage("⚡ [속도 최적화] 기존 파일 목록 캐시 구축 중...");
          var folderCache = getFolderCache(saveFolder);
          logMessage("✅ 기존 파일 목록 " + folderCache.names.length + "개 메모리 로드 완료\n");

          for (var c = 0; c < activeCollectors.length; c++) {
            if (isStopRequested()) {
              logMessage("🛑 [중단 요청 감지] 수집 작업이 강제 중단되었습니다.");
              stoppedEarly = true;
              break;
            }

            if (new Date().getTime() - startTime > maxTimeMs) {
              logMessage("⚠️ [구글 서버 실행 시간제한(4분 40초) 감지] 구글 스크립트 6분 자동 강제종료 타임아웃을 방지하기 위해 현재 수집 단계에서 작업을 정돈합니다.");
              timeLimitReached = true;
              stoppedEarly = true;
              break;
            }

            var collector = activeCollectors[c];
            try {
              var cnt = collector.fetch(saveFolder, targetDt, collectorLogFn, folderCache);
              dayDownloaded += cnt;
            } catch (e) {
              logMessage("❌ [오류] " + collector.name + " (" + dateStr + ") 수집 중 예외 발생: " + e.toString() + "\n");
            }
          }
        }
      }

      totalDownloaded += dayDownloaded;

      // 2. AI 리포트 분석 및 요약 기능 (체크 시 실행)
      if (enableAiSummary && !timeLimitReached) {
        var folderCache = folderCache || getFolderCache(saveFolder);
        var hasPdfs = folderCache && folderCache.names && folderCache.names.length > 0;
        var summaryFolder = getOrCreateSummaryFolder(config);
        var summaryPdfName = dateStr + "_증권리포트_요약집.pdf";
        var summaryExists = summaryFolder.getFilesByName(summaryPdfName).hasNext();

        if (dayDownloaded > 0 || (hasPdfs && !summaryExists) || !enableDownload) {
          logMessage("🤖 [" + dateStr + "] Gemini AI 증시현황 요약집(PDF & DOC) 분석 생성을 가동합니다...");
          try {
            var summaryRes = generateOrUpdateDailySummary(config, targetDt, saveFolder, logMessage);
            if (summaryRes) {
              latestSummaryInfo = summaryRes;
              logMessage("🎉 [" + dateStr + "] Gemini AI 증시현황 요약집 자동 업그레이드 완료!");
            }
          } catch (sumErr) {
            logMessage("⚠️ [" + dateStr + "] AI 요약집 자동 생성 중 예외: " + sumErr.toString());
          }
        }
      }

      logMessage("📊 <<< [" + dateStr + " 작업 완료] 일자별 다운로드: " + dayDownloaded + "개\n");

      if (stoppedEarly) break;
    }

    logMessage("📊 ==========================================");
    if (stoppedEarly) {
      if (timeLimitReached) {
        logMessage("⏱️ [시간제한으로 부분 완료] 구글 서버 6분 타임아웃 방지를 위해 수집 및 요약 내역(총 " + totalDownloaded + "개 다운로드)이 안전하게 구글 드라이브 및 달력에 정돈되었습니다.");
        logMessage("💡 팁: 남은 기간이 있는 경우 [🚀 즉시 수집 실행]을 한 번 더 누르시면 기존 다운로드분을 자동 스킵하고 연속하여 남은 일자 수집이 진행됩니다.");
      } else {
        logMessage("🛑 [작업 중단됨] 사용자의 강제 중단 요청에 의해 정지되었습니다. (총 다운로드: " + totalDownloaded + "개)");
      }
    } else {
      if (enableDownload && enableAiSummary) {
        logMessage("📊 [전체 작업 완료] 총 신규 다운로드 " + totalDownloaded + "개 및 Gemini AI 요약 작성 완수!");
      } else if (enableDownload) {
        logMessage("📊 [전체 수집 완료] 총 신규 다운로드: " + totalDownloaded + "개");
      } else if (enableAiSummary) {
        logMessage("📊 [전체 AI 요약 완료] Gemini AI 요약 분석 작성이 완료되었습니다.");
      }
    }
    logMessage("📊 ==========================================\n");

    // ⚡ [달력 캐시 자동 갱신] 수집 및 요약 완료 후 달력 인덱스 캐시 갱신
    try {
      refreshCalendarIndexCache(config);
    } catch (e) {
      // ignore
    }

    // 📱 [텔레그램 수집 알림] 신규 수집 리포트가 1건 이상일 때 텔레그램 메시지 전송
    if (!stoppedEarly && totalDownloaded > 0 && config.telegram_enabled && config.telegram_token && config.telegram_chat_id) {
      var dRangeStr = "";
      if (targetDates.length > 1) {
        dRangeStr = Utilities.formatDate(targetDates[0], "Asia/Seoul", "yyyy-MM-dd") + " ~ " + Utilities.formatDate(targetDates[targetDates.length - 1], "Asia/Seoul", "yyyy-MM-dd");
      } else {
        dRangeStr = Utilities.formatDate(targetDates[0], "Asia/Seoul", "yyyy-MM-dd");
      }

      var tgMsg = "<b>📥 [증권 리포트 신규 수집 완료 알림]</b>\n\n" +
        "📅 <b>수집 일자:</b> " + dRangeStr + "\n" +
        "📁 <b>구글 드라이브:</b> " + (saveFolder ? saveFolder.getName() : "증권사별리포트") + "\n" +
        "📥 <b>신규 수집:</b> 총 " + totalDownloaded + "개 리포트 수집 완료\n" +
        "⏱️ <b>동작 모드:</b> " + (isScheduled ? config.interval_minutes + "분 자동 반복 수집" : "수동 즉시 수집");

      if (downloadedReportTitles && downloadedReportTitles.length > 0) {
        tgMsg += "\n\n<b>📄 수집된 신규 리포트 주요 목록:</b>\n";
        var maxShow = Math.min(downloadedReportTitles.length, 10);
        for (var tIdx = 0; tIdx < maxShow; tIdx++) {
          tgMsg += "�� " + downloadedReportTitles[tIdx] + "\n";
        }
        if (downloadedReportTitles.length > 10) {
          tgMsg += "• ... 외 " + (downloadedReportTitles.length - 10) + "건 추가 수집됨";
        }
      }

      var res = sendTelegramMessage(config.telegram_token, config.telegram_chat_id, tgMsg);
      if (res.success) {
        logMessage("📱 [텔레그램 알림] 신규 리포트 수집 완료 메세지 전송 성공! ✅\n");
      } else {
        logMessage("📱 [텔레그램 알림] 수집 알림 전송 실패: " + res.error + " ⚠️\n");
      }
    }

    logMessage(stoppedEarly ? "🛑 [수집 중단 처리 완료]" : "🏁 [모든 수집 및 요약 정리 완료]");
    return { count: totalDownloaded, logs: currentLogs };
  } finally {
    try {
      refreshCalendarIndexCache(config);
    } catch (e) {}
    setRunningFlag(false);
    clearStopRequested();
  }
}

function runStockReportScheduled() {
  runStockReport(true);
}

function runStockReportManualTask() {
  clearManualTaskTriggers();
  try {
    runStockReport(false);
  } catch (e) {
    logMessage("❌ [작업 실패 예외] " + e.toString());
  } finally {
    setRunningFlag(false);
    clearStopRequested();
  }
}

function clearManualTaskTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "runStockReportManualTask") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function executeNow() {
  var config = getConfig();
  var enableDownload = config.enable_report_download !== false;
  var enableAiSummary = config.enable_ai_summary !== false;
  var taskName = "수집 및 AI 요약";
  if (enableDownload && !enableAiSummary) taskName = "리포트 다운로드 수집";
  else if (!enableDownload && enableAiSummary) taskName = "Gemini AI 요약 분석";

  saveRecentLogs(["🚀 [즉시 실행 요청] " + taskName + " 작업을 구글 서버 백그라운드에서 시작합니다..."]);
  setRunningFlag(true);
  clearStopRequested();

  ScriptApp.newTrigger("runStockReportManualTask")
    .timeBased()
    .after(100)
    .create();

  return { status: "started" };
}

function requestStop() {
  try {
    var props = PropertiesService.getUserProperties();
    props.setProperty("STOP_REQUESTED", "true");
    logMessage("🛑 [사용자 요청] 수집 및 AI 요약 작업 강제 중단 요청을 수신했습니다...");
    return { success: true };
  } catch (e) {
    return { success: false, error: e.toString() };
  }
}

function isStopRequested() {
  try {
    var props = PropertiesService.getUserProperties();
    return props.getProperty("STOP_REQUESTED") === "true";
  } catch (e) {
    return false;
  }
}

function clearStopRequested() {
  try {
    var props = PropertiesService.getUserProperties();
    props.setProperty("STOP_REQUESTED", "false");
  } catch (e) {
    // ignore
  }
}

function isTaskRunning() {
  try {
    var props = PropertiesService.getUserProperties();
    return props.getProperty("IS_RUNNING") === "true";
  } catch (e) {
    return false;
  }
}

function setRunningFlag(val) {
  try {
    var props = PropertiesService.getUserProperties();
    props.setProperty("IS_RUNNING", val ? "true" : "false");
  } catch (e) {
    // ignore
  }
}

function getActiveCollectors(config) {
  var list = [];
  var sel = config.selected_sites || {};
  var maxPages = (config.date_mode === "today") ? 1 : 3;

  if (sel["교보증권"]) {
    list.push({ name: "교보증권", fetch: function(folder, dt, logFn, cache) { return fetchKyobo(folder, dt, logFn, cache); } });
  }
  if (sel["미래에셋증권"]) {
    list.push({ name: "미래에셋증권", fetch: function(folder, dt, logFn, cache) { return fetchMirae(folder, dt, logFn, cache); } });
  }
  if (sel["한경 컨센서스"]) {
    list.push({ name: "한경 컨센서스", fetch: function(folder, dt, logFn, cache) { return fetchHankyung(folder, dt, logFn, cache); } });
  }

  for (var i = 0; i < NAVER_CATEGORIES.length; i++) {
    var cat = NAVER_CATEGORIES[i];
    if (sel[cat.config_key]) {
      (function(categoryInfo) {
        list.push({
          name: "네이버 " + categoryInfo.display_name,
          fetch: function(folder, dt, logFn, cache) {
            return fetchNaverCategory(categoryInfo, folder, dt, logFn, maxPages, cache);
          }
        });
      })(cat);
    }
  }

  return list;
}

function toggleScheduler(enable) {
  var config = getConfig();
  var interval = parseInt(config.interval_minutes, 10);
  if (isNaN(interval) || interval <= 0) interval = 30;

  if (enable) {
    setupTrigger(interval);
    logMessage("🟢 [" + interval + "분 주기] 백그라운드 자동 수집 스케줄러가 활성화되었습니다.");
    return {
      active: true,
      interval: interval,
      message: "🟢 " + interval + "분 주기 백그라운드 자동 수집 스케줄러 구동 중"
    };
  } else {
    clearTriggers();
    config.interval_minutes = 0;
    saveConfig(config);
    logMessage("🔴 백그라운드 자동 수집 스케줄러가 완전히 정지되었습니다.");
    return {
      active: false,
      interval: 0,
      message: "🔴 백그라운드 자동 수집 정지됨 (수동 실행 전용)"
    };
  }
}

function setupTrigger(minutes) {
  clearTriggers();
  var interval = parseInt(minutes, 10) || 0;

  var config = getConfig();
  config.interval_minutes = interval;
  saveConfig(config);

  if (interval > 0) {
    if (interval < 60) {
      ScriptApp.newTrigger("runStockReportScheduled")
        .timeBased()
        .everyMinutes(interval)
        .create();
    } else {
      var hours = Math.floor(interval / 60);
      ScriptApp.newTrigger("runStockReportScheduled")
        .timeBased()
        .everyHours(hours)
        .create();
    }
    return "✅ " + interval + "분 주기 자동 수집 스케줄러가 등록되었습니다.";
  } else {
    return "🛑 자동 수집 스케줄러가 해제되었습니다.";
  }
}

function clearTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "runStockReportScheduled") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function getAppConfig() {
  return getConfig();
}

function saveAppConfig(newConfig) {
  var saved = saveConfig(newConfig);
  if (saved.interval_minutes !== undefined) {
    setupTrigger(saved.interval_minutes);
  }
  return saved;
}

function getCalendarData(year, month) {
  var config = getConfig();
  return getSummaryCalendarData(year, month, config);
}

function forceRefreshCalendarIndex() {
  var config = getConfig();
  var cacheData = refreshCalendarIndexCache(config);
  return { success: true, count: Object.keys(cacheData.folderMap).length };
}



function saveRecentLogs(logs) {
  try {
    var props = PropertiesService.getUserProperties();
    props.setProperty("RECENT_LOGS", JSON.stringify(logs.slice(-200)));
  } catch (e) {
    // ignore
  }
}

function getExecutionLogs() {
  try {
    var props = PropertiesService.getUserProperties();
    var raw = props.getProperty("RECENT_LOGS");
    var logs = raw ? JSON.parse(raw) : [];
    var running = isTaskRunning();
    return { logs: logs, running: running };
  } catch (e) {
    return { logs: [], running: false };
  }
}

function debugReadTargetDoc() {
  var res = {};
  try {
    var doc1 = DocumentApp.openById("1bo8is75wYCLOP0JFcjj2K7Lvhkqgi2bcsZmhsraClew");
    res.targetDocText = doc1.getBody().getText();
  } catch(e) {
    res.targetDocErr = e.toString();
  }

  return res;
}

/**
 * 🤖 특정 일자의 수집된 모든 PDF 리포트를 소스로 Gemini AI 요약(PDF & DOC) 생성
 */
function regenerateSummaryForDate(dateStr) {
  try {
    logMessage("🤖 [" + dateStr + "] Gemini AI 리포트 요약 분석 스레드를 가동합니다...");
    setRunningFlag(true);
    clearStopRequested();

    var config = getConfig();
    var targetDt = parseDateString(dateStr);
    var saveFolder = getEffectiveSaveFolder(config, targetDt);

    var summaryRes = generateOrUpdateDailySummary(config, targetDt, saveFolder, logMessage);

    // 달력 인덱스 캐시 실시간 갱신 및 로깅
    try {
      logMessage("⚡ [달력 인덱스 실시간 갱신] 요약 작업 완수! 달력 데이터를 실시간 업데이트합니다.");
      refreshCalendarIndexCache(config);
      logMessage("✅ [달력 인덱스 갱신 완수] AI 요약 보고서 달력 보드가 최신 상태로 반영되었습니다.");
    } catch (e) {
      logMessage("⚠️ [달력 인덱스 갱신 예외] " + e.toString());
    }

    setRunningFlag(false);
    clearStopRequested();

    if (summaryRes) {
      logMessage("🎉 [" + dateStr + "] Gemini AI 증권 리포트 요약집 완수!");

      // 📱 텔레그램 알림 전송 (단일 날짜 요약 완수 시)
      if (config.telegram_enabled && config.telegram_token && config.telegram_chat_id) {
        try {
          var tgMsg = "<b>🤖 [" + dateStr + " Gemini AI 증권 리포트 요약 완료]</b>\n\n" +
            "📄 <b>PDF 요약집:</b>\n<a href=\"" + summaryRes.fileUrl + "\">" + summaryRes.fileName + "</a>\n\n" +
            "📝 <b>MD 마크다운 요약문서:</b>\n<a href=\"" + (summaryRes.mdUrl || summaryRes.docUrl) + "\">" + (summaryRes.mdFileName || "마크다운 문서") + "</a>";
          sendTelegramMessage(config.telegram_token, config.telegram_chat_id, tgMsg);
        } catch (tgErr) {}
      }

      return {
        success: true,
        fileUrl: summaryRes.fileUrl,
        docUrl: summaryRes.docUrl,
        mdUrl: summaryRes.mdUrl,
        fileName: summaryRes.fileName
      };
    } else {
      return {
        success: false,
        error: "해당 일자의 리포트를 찾지 못했거나 AI 요약 생성에 실패했습니다."
      };
    }
  } catch (e) {
    logMessage("❌ [AI 요약 예외] " + e.toString());
    return { success: false, error: e.toString() };
  } finally {
    try {
      var cfg = config || getConfig();
      logMessage("⚡ [달력 인덱스 최종 동기화] 요약 분석 스레드가 정상 종료되어 달력 데이터 인덱스를 최종 동기화합니다.");
      refreshCalendarIndexCache(cfg);
    } catch (err) {}
    setRunningFlag(false);
    clearStopRequested();
  }
}

/**
 * 📱 텔레그램 알림 발송 테스트 RPC 헨들러
 */
function testTelegramNotification(customConfig) {
  var config = customConfig || getConfig();
  if (!config.telegram_enabled) {
    return { success: false, error: "텔레그램 알림 기능이 비활성화되어 있습니다." };
  }
  if (!config.telegram_token || !config.telegram_chat_id) {
    return { success: false, error: "Bot Token 또는 Chat ID가 설정되지 않았습니다." };
  }

  var testMsg = "<b>📱 [StockReport 텔레그램 연동 테스트]</b>\n\n" +
    "✅ 텔레그램 봇 알림 기능이 정상적으로 동작하고 있습니다!\n" +
    "⏱️ <b>발송 일시:</b> " + Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss") + "\n" +
    "🤖 <b>Gemini AI 모델:</b> " + (config.gemini_model || "gemini-flash-latest");

  return sendTelegramMessage(config.telegram_token, config.telegram_chat_id, testMsg);
}
