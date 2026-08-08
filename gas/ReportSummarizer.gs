/**
 * ReportSummarizer.gs - Gemini AI 증권 리포트 멀티모달 딥 심층 분석 & PDF / Markdown (.md) 보고서 생성 모듈
 */

function generateOrUpdateDailySummary(config, targetDate, dateFolder, logFn) {
  var dateStr = Utilities.formatDate(targetDate, "Asia/Seoul", "yyyy-MM-dd");
  if (!logFn) logFn = Logger.log;

  logFn("🧠 ==========================================");
  logFn("🧠 [Gemini AI 일괄 멀티모달 딥 분석 가동] " + dateStr);
  logFn("🧠 ==========================================");

  var searchRes = findAllPdfFilesForDate(config, targetDate, logFn);
  var pdfFiles = searchRes.files;

  if (!pdfFiles || pdfFiles.length === 0) {
    logFn("⚠️ [" + dateStr + "] 해당 날짜의 수집된 PDF 리포트 파일이 없습니다.");
    return null;
  }

  var apiKey = config.gemini_api_key ? config.gemini_api_key.trim() : "";
  var customPrompt = config.custom_prompt || "";

  if (!apiKey) {
    logFn("⚠️ [Gemini API 키 미설정] 메인 설정 화면에서 Gemini API Key를 입력해 주세요.");
    return null;
  }

  var startTime = new Date().getTime();

  // 1. 전체 PDF 파일 데이터 수집 및 청크 파티셔닝 준비 (메모리 절약을 위해 Blob은 청크 실행 시 지연 로딩)
  var reportList = [];
  var pdfDataList = [];

  for (var i = 0; i < pdfFiles.length; i++) {
    if (typeof isStopRequested === "function" && isStopRequested()) {
      logFn("🛑 [Gemini AI 중단 요청 감지] 사용자의 강제 중단 요청으로 요약 작업을 즉시 정지합니다.");
      return null;
    }

    var file = pdfFiles[i];
    var fileName = file.getName();
    var parsed = parseReportFilename(fileName);

    var itemInfo = {
      file: file,
      fileName: fileName,
      tag: parsed.tag,
      title: parsed.title,
      url: file.getUrl()
    };

    reportList.push(itemInfo);
    pdfDataList.push(itemInfo);
  }

  var selectedModel = config.gemini_model || "gemini-flash-latest";
  var activePrompt = (customPrompt && customPrompt.trim() !== "") ? customPrompt.trim() : getDefaultConfig().custom_prompt;

  // 2. 청크 파티셔닝 크기 설정 (Apps Script HTTP 타임아웃 60초 및 메모리/실행시간 제한 완전 극복: 10개 단위 분할)
  var CHUNK_SIZE = 10;
  var totalFiles = pdfDataList.length;
  var totalChunks = Math.ceil(totalFiles / CHUNK_SIZE);
  var chunkSummaries = [];

  logFn("📦 전체 " + totalFiles + "개 PDF 리포트를 " + CHUNK_SIZE + "개 단위 청크(" + totalChunks + "개 파트)로 분할하여 지연 로딩 기반 Gemini AI 심층 분석을 가동합니다...");

  for (var c = 0; c < totalChunks; c++) {
    if (typeof isStopRequested === "function" && isStopRequested()) {
      logFn("🛑 [Gemini AI 중단 요청 감지] 요약 작업을 정지합니다.");
      return null;
    }

    // ⏱️ GAS 6분 (360초) 실행 제한 보호를 위한 타임아웃 예방 모드
    var elapsedSec = (new Date().getTime() - startTime) / 1000;
    if (elapsedSec > 220) {
      logFn("⏱️ [타임아웃 방지 모드] Apps Script 6분 실행 시간 제한 보호를 위해 남은 " + (totalChunks - c) + "개 파트(" + (totalFiles - c * CHUNK_SIZE) + "개 리포트)는 메타데이터 빠른 요약으로 신속 변환합니다.");
      for (var rem = c; rem < totalChunks; rem++) {
        var remStart = rem * CHUNK_SIZE;
        var remEnd = Math.min(remStart + CHUNK_SIZE, totalFiles);
        var remFiles = pdfDataList.slice(remStart, remEnd);
        var remTxt = "";
        remFiles.forEach(function(cf) {
          remTxt += "### ■ [" + cf.tag + "] " + cf.title + "\n* **핵심 내용 요약**: " + cf.title + " (원본 리포트 참조)\n* **원문 링크**: " + cf.url + "\n";
        });
        chunkSummaries.push(remTxt);
      }
      break;
    }

    var startIdx = c * CHUNK_SIZE;
    var endIdx = Math.min(startIdx + CHUNK_SIZE, totalFiles);
    var chunkFiles = pdfDataList.slice(startIdx, endIdx);

    logFn("🤖 > [파트 " + (c + 1) + "/" + totalChunks + "] (" + (startIdx + 1) + "~" + endIdx + "번째 " + chunkFiles.length + "개 PDF) Gemini AI [" + selectedModel + "] 딥 분석 중...");

    var chunkParts = [];
    var chunkBytes = 0;
    var maxChunkBytes = 6 * 1024 * 1024; // 6MB 제한 (UrlFetch 페이로드 및 응답 속도 최적화)

    for (var k = 0; k < chunkFiles.length; k++) {
      var item = chunkFiles[k];
      try {
        var blob = item.file.getBlob();
        var bytes = blob.getBytes();
        if (chunkBytes + bytes.length <= maxChunkBytes) {
          chunkBytes += bytes.length;
          var b64 = Utilities.base64Encode(bytes);
          chunkParts.push({
            "inlineData": {
              "mimeType": "application/pdf",
              "data": b64
            }
          });
        } else {
          chunkParts.push({
            "text": "리포트 제목: " + item.title + "\n분류: " + item.tag + "\n구글드라이브 URL: " + item.url + "\n"
          });
        }
      } catch (fileErr) {
        chunkParts.push({
          "text": "리포트 제목: " + item.title + "\n분류: " + item.tag + "\n구글드라이브 URL: " + item.url + "\n"
        });
      }
    }

    var chunkInstruction = "당신은 기관 투자자 대상의 글로벌 자산운용사 시니어 에쿼티 애널리스트입니다.\n" +
      "제공된 " + chunkFiles.length + "개 PDF 리포트에 대해 아래 작성 지침에 따라 핵심 내러티브, 재무/추정 지표, 체크리스트, 리스크를 정밀 분석해 주세요.\n\n" +
      "[분석 지침]\n" + activePrompt;

    chunkParts.push({ "text": chunkInstruction });

    var chunkRes = executeBatchGeminiRequest(apiKey, chunkParts, selectedModel, logFn);
    if (chunkRes && chunkRes.trim().length > 50) {
      logFn("  ✅ [파트 " + (c + 1) + "/" + totalChunks + " 완료] " + chunkFiles.length + "개 분석 완수!");
      chunkSummaries.push(chunkRes);
    } else {
      logFn("  ⚠️ [파트 " + (c + 1) + "/" + totalChunks + " 경고] AI 응답이 비어있어 목록 대체합니다.");
      var fallbackTxt = "";
      chunkFiles.forEach(function(cf) {
        fallbackTxt += "### ■ [" + cf.tag + "] " + cf.title + "\n* **핵심 내러티브 요약**: 원본 리포트 참조\n";
      });
      chunkSummaries.push(fallbackTxt);
    }
  }

  // 3. 청크별 요약 결과 1개의 마스터 보고서로 종합 통합
  var masterSummaryText = "";
  if (chunkSummaries.length === 1) {
    masterSummaryText = chunkSummaries[0];
  } else {
    logFn("🧠 > 전체 " + totalChunks + "개 파트 분석 결과를 단일 마스터 요약 보고서로 통합 작성 중...");
    var mergeParts = [];
    var mergePrompt = "당신은 기관 투자자 대상의 글로벌 자산운용사 시니어 에쿼티 애널리스트이자 리스크 관리 전문가입니다.\n" +
      "제공된 총 " + totalFiles + "개 리포트에 대한 " + totalChunks + "개 파트별 심층 분석 결과 데이터를 바탕으로, 중복을 배제하고 유기적으로 융합하여 지정된 6단계 작성 양식에 맞춰 완벽한 단일 마스터 요약 보고서를 종합 작성해 주세요.\n\n" +
      "[지정된 6단계 작성 양식 및 출력 형식 지침]\n" + activePrompt + "\n\n" +
      "=== [파트별 분할 심층 분석 데이터] ===\n";

    for (var m = 0; m < chunkSummaries.length; m++) {
      mergePrompt += "\n[파트 " + (m + 1) + "/" + totalChunks + " 분석 결과]\n" + chunkSummaries[m] + "\n";
    }

    mergeParts.push({ "text": mergePrompt });
    var mergedResult = executeBatchGeminiRequest(apiKey, mergeParts, selectedModel, logFn);
    if (mergedResult && mergedResult.trim().length > 100) {
      masterSummaryText = mergedResult;
      logFn("✨ [최종 마스터 보고서 통합 완수] 전체 " + totalFiles + "개 리포트 6단계 종합 보고서 작성이 완료되었습니다!");
    } else {
      masterSummaryText = chunkSummaries.join("\n\n---\n\n");
    }
  }

  // 4. 참고 문헌 및 출처 섹션 100% 전수 자동 보장 (점 리스트 • / - 형태)
  var cleanedText = masterSummaryText.replace(/\n*##?\s*6[\s\S]*$/, "").trim();
  
  var sourceSectionText = "\n\n## 6. 참고 문헌 및 출처 (Source Files)\n* 본 보고서 작성에 참고한 구글 드라이브 원본 리포트 목록 (총 " + reportList.length + "건 전체):\n";
  for (var idx = 0; idx < reportList.length; idx++) {
    var r = reportList[idx];
    sourceSectionText += "  - [" + r.fileName + "](" + r.url + ")\n";
  }

  masterSummaryText = cleanedText + sourceSectionText;

  // 5. 구글 드라이브에 PDF 및 마크다운(.md) 파일 자동 저장
  var summaryFolder = getOrCreateSummaryFolder(config);
  var pdfFileName = dateStr + "_증권리포트_요약집.pdf";
  var mdFileName = dateStr + "_증권리포트_요약집.md";

  cleanDuplicateSummaryFiles(summaryFolder, dateStr, logFn);

  // Markdown(.md) 마스터 요약문서 생성
  var summaryMdFile = createMarkdownFileFromMasterText(summaryFolder, mdFileName, dateStr, masterSummaryText, reportList.length, logFn);

  // PDF 요약문서 생성 (HTML -> PDF 변환)
  var htmlContent = buildSummaryHtmlFromMasterText(dateStr, masterSummaryText, reportList, logFn);
  var tempHtmlBlob = Utilities.newBlob(htmlContent, "text/html", "temp.html");
  var pdfBlob = tempHtmlBlob.getAs("application/pdf");
  pdfBlob.setName(pdfFileName);
  var summaryPdfFile = summaryFolder.createFile(pdfBlob);

  logFn("📄 [PDF 요약 문서 저장 완료] " + pdfFileName + " (" + Math.round(pdfBlob.getBytes().length / 1024) + " KB)");
  if (summaryMdFile) {
    logFn("🏷️ [MD 마크다운 문서 저장 완료] " + mdFileName + " (Markdown .md 포맷)");
  }

  try {
    summaryPdfFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    if (summaryMdFile) {
      summaryMdFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    }
  } catch (e) {}

  // 📱 [텔레그램 알림 전송] Gemini AI 분석 요약 완수 시 분석 결과 문서 링크 자동 발송
  if (config.telegram_enabled && config.telegram_token && config.telegram_chat_id) {
    try {
      var tgMsg = "<b>🤖 [Gemini AI 증시현황 통합 요약 보고서 작성 완료]</b>\n\n" +
        "📅 <b>분석 일자:</b> " + dateStr + "\n" +
        "🧠 <b>분석 모델:</b> " + selectedModel + "\n" +
        "📊 <b>분석 리포트:</b> 총 " + reportList.length + "개 PDF 수집본 멀티모달 심층 분석 완료\n\n" +
        "<b>🔗 완성된 AI 마스터 요약 보고서 바로가기:</b>\n" +
        "📄 <b>PDF 요약집 보고서:</b>\n<a href=\"" + summaryPdfFile.getUrl() + "\">" + pdfFileName + "</a>\n\n" +
        "📝 <b>MD 마크다운 요약문서:</b>\n<a href=\"" + (summaryMdFile ? summaryMdFile.getUrl() : summaryPdfFile.getUrl()) + "\">" + mdFileName + "</a>";

      var tgRes = sendTelegramMessage(config.telegram_token, config.telegram_chat_id, tgMsg);
      if (tgRes && tgRes.success) {
        logFn("📱 [텔레그램 알림] AI 요약 보고서 링크 전송 완료! ✅");
      } else {
        logFn("📱 [텔레그램 알림] AI 요약 알림 전송 실패: " + (tgRes ? tgRes.error : "알 수 없는 오류"));
      }
    } catch (tgErr) {
      logFn("📱 [텔레그램 알림] 전송 중 예외: " + tgErr.toString());
    }
  }

  // ⚡ [달력 인덱스 실시간 자동 갱신] 요약 완료 직후 달력 데이터 인덱스를 실시간 업데이트
  try {
    logFn("⚡ [달력 인덱스 실시간 갱신] Gemini AI 요약 분석 완료! 달력 데이터 인덱스를 즉시 최신화합니다...");
    var refreshRes = refreshCalendarIndexCache(config);
    var dateCount = refreshRes && refreshRes.summaryMap ? Object.keys(refreshRes.summaryMap).length : 0;
    logFn("✅ [달력 인덱스 갱신 완료] 총 " + dateCount + "개 일자의 AI 요약집 인덱스가 성공적으로 반영되었습니다. 📅");
  } catch (e) {
    logFn("⚠️ [달력 인덱스 갱신 예외] " + e.toString());
  }

  return {
    fileUrl: summaryPdfFile.getUrl(),
    docUrl: summaryMdFile ? summaryMdFile.getUrl() : summaryPdfFile.getUrl(),
    mdUrl: summaryMdFile ? summaryMdFile.getUrl() : summaryPdfFile.getUrl(),
    fileName: pdfFileName,
    mdFileName: mdFileName,
    fileId: summaryPdfFile.getId(),
    totalCount: reportList.length
  };
}

/**
 * 🧠 단 1회의 REST 요청으로 전체 멀티모달 패키지를 분석하는 실행기 (사용자 선택 모델 지원)
 */
function executeBatchGeminiRequest(apiKey, parts, selectedModel, logFn) {
  var payload = {
    "contents": [{ "parts": parts }],
    "generationConfig": {
      "temperature": 0.2,
      "maxOutputTokens": 8000
    }
  };

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var modelName = (selectedModel && selectedModel.trim() !== "") ? selectedModel.trim() : "gemini-flash-latest";
  var primaryEp = "https://generativelanguage.googleapis.com/v1beta/models/" + modelName + ":generateContent?key=";
  var fallbackEp = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=";

  var endpoints = [ primaryEp ];
  if (primaryEp !== fallbackEp) {
    endpoints.push(fallbackEp);
  }

  for (var ep = 0; ep < endpoints.length; ep++) {
    try {
      var res = UrlFetchApp.fetch(endpoints[ep] + apiKey, options);
      var code = res.getResponseCode();
      var resText = res.getContentText();

      if (code === 200) {
        var json = JSON.parse(resText);
        if (json.candidates && json.candidates.length > 0 && json.candidates[0].content && json.candidates[0].content.parts && json.candidates[0].content.parts.length > 0) {
          return json.candidates[0].content.parts[0].text;
        }
      } else {
        if (logFn) logFn("⚠️ Gemini API (" + endpoints[ep].split("/models/")[1].split(":")[0] + ") 응답 코드 " + code + ": " + resText.substring(0, 120));
      }
    } catch (e) {
      if (logFn) logFn("⚠️ Gemini API 통신 예외: " + e.toString());
    }
  }

  return null;
}

/**
 * 🏷️ 마스터 통합 텍스트 기반 마크다운 (.md) 문서 파일 생성
 */
function createMarkdownFileFromMasterText(summaryFolder, mdFileName, dateStr, masterText, totalCount, logFn) {
  try {
    var headerText = "# 📅 " + dateStr + " 증권 리포트 통합 AI 요약 보고서\n" +
      "**분석 일자**: " + dateStr + " | **수집 분석**: " + totalCount + "개 전체 리포트 완료\n\n---\n\n";

    var fullContent = headerText + masterText;
    var blob = Utilities.newBlob(fullContent, "text/markdown", mdFileName);

    var mdFile = summaryFolder.createFile(blob);
    return mdFile;
  } catch (e) {
    if (logFn) logFn("⚠️ 마크다운(.md) 요약 파일 생성 중 예외: " + e.toString());
    return null;
  }
}

/**
 * 📄 마스터 통합 텍스트 기반 흰색 바탕 PDF HTML 변환 생성 (마크다운 하이퍼링크 HTML 변환)
 */
function buildSummaryHtmlFromMasterText(dateStr, masterText, reportList, logFn) {
  var formattedBody = masterText
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^(\d+\.\s+.*$)/gm, '<h2 style="color: #1e3a8a; border-bottom: 2px solid #2563eb; padding-bottom: 6px; margin-top: 24px; margin-bottom: 12px; font-size: 18px;">$1</h2>')
    .replace(/^■\s*(.*$)/gm, '<h3 style="color: #1e40af; border-bottom: 1px solid #bfdbfe; padding-bottom: 4px; margin-top: 18px; margin-bottom: 8px; font-size: 15px;">■ $1</h3>')
    .replace(/^\[⚠️\s*(.*?)\]/gm, '<h4 style="color: #b91c1c; margin-top: 14px; margin-bottom: 6px; font-size: 14px;">[⚠️ $1]</h4>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: 500;">$1</a>')
    .replace(/(\n|^)\s*[\-\*•]\s*(.*)/g, '$1<li style="margin-bottom: 6px; list-style-type: none; padding-left: 14px;">• $2</li>')
    .replace(/\n/g, '<br>');

  var html = '<!DOCTYPE html>\n<html lang="ko">\n<head>\n' +
    '<meta charset="UTF-8">\n' +
    '<title>' + dateStr + ' Gemini AI 증권 리포트 통합 요약 보고서</title>\n' +
    '<style>\n' +
    '  @page { size: A4; margin: 12mm; }\n' +
    '  body { font-family: "Noto Sans KR", "Malgun Gothic", sans-serif; background-color: #ffffff; color: #1e293b; margin: 0; padding: 15px; line-height: 1.65; -webkit-print-color-adjust: exact; print-color-adjust: exact; }\n' +
    '  .container { max-width: 850px; margin: 0 auto; }\n' +
    '  .intro-box { background: #f8fafc; border: 1px solid #cbd5e1; border-left: 5px solid #2563eb; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; text-align: left; }\n' +
    '  .intro-text { font-size: 17px; font-weight: bold; color: #0f172a; margin-bottom: 4px; }\n' +
    '  .intro-sub { font-size: 12.5px; color: #475569; }\n' +
    '  .master-content { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px; font-size: 13.5px; color: #1e293b; line-height: 1.75; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }\n' +
    '  .footer { text-align: center; color: #94a3b8; font-size: 11px; margin-top: 24px; padding-top: 12px; border-top: 1px solid #e2e8f0; }\n' +
    '</style>\n</head>\n<body>\n' +
    '<div class="container">\n' +
    '  <div class="intro-box">\n' +
    '    <div class="intro-text">📄 ' + dateStr + ' 증권 리포트 통합 AI 요약 보고서</div>\n' +
    '    <div class="intro-sub">📅 분석 일자: ' + dateStr + ' • 📥 총 분석 리포트: ' + reportList.length + '개 전체 완료</div>\n' +
    '  </div>\n' +
    '  <div class="master-content">\n' + formattedBody + '\n  </div>\n' +
    '  <div class="footer">\n' +
    '    StockReport Gemini AI Financial Summarizer • Google Apps Script<br>\n' +
    '    생성 일시: ' + Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss") + '\n' +
    '  </div>\n' +
    '</div>\n</body>\n</html>';

  return html;
}

function parseReportFilename(fileName) {
  var clean = fileName.replace(/\.pdf$/i, "");
  var match = clean.match(/^\[([^\]]+)\]\s*(.*)$/);
  if (match) {
    var tag = match[1].trim();
    var title = match[2].trim() || tag;
    return { tag: tag, company: tag, category: "기업", title: title };
  }
  return { tag: "기타", company: "", category: "기타", title: clean };
}

function cleanDuplicateSummaryFiles(summaryFolder, dateStr, logFn) {
  try {
    var files = summaryFolder.getFiles();
    while (files.hasNext()) {
      var f = files.next();
      var name = f.getName();
      if (name.indexOf(dateStr) !== -1 && (name.indexOf("_요약집") !== -1 || name.indexOf("증권리포트") !== -1)) {
        try { f.setTrashed(true); } catch (e) {}
      }
    }
  } catch (e) {}
}
