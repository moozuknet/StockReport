/**
 * MiraeCollector.gs - 미래에셋증권 투자정보 수집기
 */

function fetchMirae(saveFolder, targetDt, logFn, folderCache) {
  var todayDot = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy.MM.dd");
  var todayDash = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy-MM-dd");
  logFn("📌 --- [미래에셋증권] 수집 시작 (" + todayDot + ") ---");

  var url = "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521";
  var userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
  var headers = {
    "User-Agent": userAgent,
    "Referer": "https://securities.miraeasset.com/"
  };

  var count = 0;

  try {
    var response = UrlFetchApp.fetch(url, { headers: headers, muteHttpExceptions: true });
    if (response.getResponseCode() !== 200) {
      logFn("⚠️ 미래에셋증권 접속 실패 (HTTP " + response.getResponseCode() + ")");
      return 0;
    }

    var html = response.getContentText("euc-kr");
    var trMatches = html.match(/<tr[\s\S]*?<\/tr>/gi);

    if (!trMatches || trMatches.length === 0) {
      logFn("⚠️ 미래에셋증권 목록 테이블을 찾을 수 없습니다.");
      return 0;
    }

    for (var i = 0; i < trMatches.length; i++) {
      var trHtml = trMatches[i];

      if (trHtml.indexOf(todayDot) === -1 && trHtml.indexOf(todayDash) === -1) {
        continue;
      }

      var aMatches = trHtml.match(/<a[\s\S]*?<\/a>/gi);
      if (!aMatches || aMatches.length === 0) continue;

      var rawTitleText = stripTags(aMatches[0]).trim();
      if (!rawTitleText) continue;

      var parsed = parseCompanyAndTitle(rawTitleText);
      var rawFileName = "";
      if (parsed.company) {
        rawFileName = parsed.title ? "[" + parsed.company + "] " + parsed.title + ".pdf" : "[" + parsed.company + "].pdf";
      } else {
        rawFileName = "[" + rawTitleText + "].pdf";
      }

      var fileName = cleanFilename(rawFileName);

      // 초고속 메모리 스킵 검사
      var check = isSkipTarget(folderCache, fileName, 0.95);
      if (check.skip) {
        logFn(check.isSimilar ? "📁 [유사 스킵(95%+)] " + fileName : "📁 [스킵] " + fileName);
        continue;
      }

      var pdfUrl = null;
      for (var j = 0; j < aMatches.length; j++) {
        var aHtml = aMatches[j];
        var downConfirmMatch = aHtml.match(/downConfirm\s*\(\s*['"]([^'"]+)['"]/i);
        if (downConfirmMatch) {
          pdfUrl = downConfirmMatch[1];
          break;
        }
        var hrefMatch = aHtml.match(/href=["']([^"']+\.pdf)["']/i);
        if (hrefMatch) {
          pdfUrl = makeAbsoluteUrl(url, hrefMatch[1]);
          break;
        }
      }

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
          logFn("❌ [다운로드 실패] " + fileName + ": " + e.toString());
        }
      }
    }
  } catch (e) {
    logFn("⚠️ 미래에셋 접속/파싱 오류: " + e.toString());
  }

  logFn("✅ 미래에셋증권 완료 (신규 " + count + "개 다운로드)\n");
  return count;
}
