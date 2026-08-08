/**
 * HankyungCollector.gs - 한경 컨센서스 종합 리포트 수집기 (최신 URL & REST 구조 대응)
 */

function fetchHankyung(saveFolder, targetDt, logFn, folderCache) {
  var todayDot = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy.MM.dd");
  var todayDash = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy-MM-dd");
  logFn("📌 --- [한경 컨센서스] 수집 시작 (" + todayDash + ") ---");

  var userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
  var headers = {
    "User-Agent": userAgent,
    "Referer": "https://consensus.hankyung.com/analysis/list"
  };

  var count = 0;
  var urlsToTry = [
    "https://consensus.hankyung.com/analysis/list?sdate=" + todayDash + "&edate=" + todayDash,
    "https://consensus.hankyung.com/analysis/list?sdate=" + todayDot + "&edate=" + todayDot,
    "https://consensus.hankyung.com/analysis/list",
    "https://markets.hankyung.com/consensus"
  ];

  var trMatches = null;
  var baseUrlUsed = "";
  var htmlContent = "";

  for (var u = 0; u < urlsToTry.length; u++) {
    try {
      var currentUrl = urlsToTry[u];
      var response = UrlFetchApp.fetch(currentUrl, { headers: headers, muteHttpExceptions: true });
      if (response.getResponseCode() === 200) {
        htmlContent = response.getContentText("utf-8");
        if (!htmlContent || htmlContent.length < 500) {
          htmlContent = response.getContentText("euc-kr");
        }
        var matches = htmlContent.match(/<tr[\s\S]*?<\/tr>/gi);
        if (matches && matches.length > 1) {
          trMatches = matches;
          baseUrlUsed = currentUrl;
          break;
        }
      }
    } catch (e) {
      // try next
    }
  }

  if (!trMatches || trMatches.length <= 1) {
    logFn("ℹ️ [" + todayDash + "] 한경 컨센서스 해당 일자 수집 데이터가 없거나 주말/휴일입니다.");
    return 0;
  }

  for (var i = 0; i < trMatches.length; i++) {
    var trHtml = trMatches[i];

    if (trHtml.indexOf("downpdf") === -1 && trHtml.indexOf("downobj") === -1 && trHtml.indexOf(".pdf") === -1) {
      continue;
    }

    var category = "산업";
    if (trHtml.indexOf("기업") !== -1) category = "기업";
    else if (trHtml.indexOf("산업") !== -1) category = "산업";
    else if (trHtml.indexOf("시장") !== -1) category = "시장";
    else if (trHtml.indexOf("경제") !== -1) category = "경제";

    var pdfHref = "";
    var rawTitle = "";

    var pdfMatch = trHtml.match(/href=["']([^"']*(?:downpdf|downobj|\.pdf)[^"']*)["']/i);
    if (pdfMatch) {
      pdfHref = pdfMatch[1];
    }

    var aMatches = trHtml.match(/<a[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi);
    if (aMatches) {
      for (var aIdx = 0; aIdx < aMatches.length; aIdx++) {
        var singleAMatch = aMatches[aIdx].match(/<a[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i);
        if (singleAMatch) {
          var t = stripTags(singleAMatch[2]).trim();
          if (t && !t.endsWith(".pdf") && t.length > 2 && !rawTitle) {
            rawTitle = t;
          }
        }
      }
    }

    if (!rawTitle || !pdfHref) continue;

    var rawFileName = "";
    if (category === "기업") {
      var parsed = parseCompanyAndTitle(rawTitle);
      if (parsed.company) {
        rawFileName = parsed.title ? "[" + parsed.company + "] " + parsed.title + ".pdf" : "[" + parsed.company + "].pdf";
      } else {
        rawFileName = "[" + rawTitle + "].pdf";
      }
    } else {
      rawFileName = "[" + category + "] " + rawTitle + ".pdf";
    }

    var fileName = cleanFilename(rawFileName);

    var check = isSkipTarget(folderCache, fileName, 0.95);
    if (check.skip) {
      logFn(check.isSimilar ? "📁 [유사 스킵(95%+)] " + fileName : "📁 [스킵] " + fileName);
      continue;
    }

    var pdfUrl = makeAbsoluteUrl(baseUrlUsed, pdfHref);

    if (pdfUrl) {
      try {
        var pdfResp = UrlFetchApp.fetch(pdfUrl, { headers: headers, muteHttpExceptions: true });
        if (pdfResp.getResponseCode() === 200) {
          var blob = pdfResp.getBlob();
          if (blob.getBytes().length > 1000) {
            blob.setName(fileName);
            saveFolder.createFile(blob);
            addFileToCache(folderCache, fileName);
            logFn("✅ [성공] " + fileName);
            count++;
          }
        }
      } catch (e) {
        logFn("❌ [실패] " + fileName + ": " + e.toString());
      }
    }
  }

  logFn("✅ 한경 컨센서스 완료 (신규 " + count + "개 다운로드)\n");
  return count;
}
