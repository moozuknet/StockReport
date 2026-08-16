/**
 * KyoboCollector.gs - 교보증권 리서치 센터 수집기
 */

function fetchKyobo(saveFolder, targetDt, logFn, folderCache) {
  var todaySlash = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy/MM/dd");
  var todayDot = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy.MM.dd");
  var todayDash = Utilities.formatDate(targetDt, "Asia/Seoul", "yyyy-MM-dd");
  logFn("📌 --- [교보증권] 수집 시작 (" + todayDot + ") ---");

  var url = "https://www.iprovest.com/weblogic/RSReportServlet?scr_id=10&menuCode=1&srch_db=0&QU=&DT1=&DT2=&provestz=&pageNum=1";
  var userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
  var headers = {
    "User-Agent": userAgent,
    "Referer": "https://www.iprovest.com/"
  };

  var count = 0;

  try {
    var response = UrlFetchApp.fetch(url, { headers: headers, muteHttpExceptions: true });
    if (response.getResponseCode() !== 200) {
      logFn("⚠️ 교보증권 접속 실패 (HTTP " + response.getResponseCode() + ")");
      return 0;
    }

    var html = response.getContentText("euc-kr");
    var trMatches = html.match(/<tr[\s\S]*?<\/tr>/gi);

    if (!trMatches || trMatches.length === 0) {
      logFn("⚠️ 교보증권 목록 테이블을 찾을 수 없습니다.");
      return 0;
    }

    for (var i = 0; i < trMatches.length; i++) {
      var trHtml = trMatches[i];

      if (trHtml.indexOf(todaySlash) === -1 && trHtml.indexOf(todayDot) === -1 && trHtml.indexOf(todayDash) === -1) {
        continue;
      }

      var tdMatches = trHtml.match(/<td[\s\S]*?<\/td>/gi);
      if (!tdMatches || tdMatches.length < 3) continue;

      var titleText = stripTags(tdMatches[1]).split('\n')[0].trim();
      var itemText = stripTags(tdMatches[2]).split('\n')[0].trim();

      if (!titleText) continue;

      var rawFileName = "";
      if (itemText) {
        if (titleText.startsWith(itemText)) {
          titleText = titleText.replace(new RegExp("^" + escapeRegExp(itemText) + "[\\s,;:]*"), "").trim();
        }
        rawFileName = "[" + itemText + "] " + titleText + ".pdf";
      } else {
        rawFileName = titleText + ".pdf";
      }

      var fileName = cleanFilename(rawFileName);

      // 초고속 메모리 스킵 검사
      var check = isSkipTarget(folderCache, fileName, 0.95);
      if (check.skip) {
        logFn(check.isSimilar ? "📁 [유사 스킵(95%+)] " + fileName : "📁 [스킵] " + fileName);
        continue;
      }

      var pdfUrl = null;
      var fileDownMatch = trHtml.match(/fileDown\s*\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]/i);

      if (fileDownMatch) {
        var param1 = fileDownMatch[1];
        var param2 = fileDownMatch[2];
        var pdfFile = param2.indexOf(".pdf") !== -1 ? param2 : param1;
        pdfUrl = "https://www.iprovest.com/upload/research/" + pdfFile;
      } else {
        var hrefMatch = trHtml.match(/href=["']([^"']+\.pdf)["']/i);
        if (hrefMatch) {
          pdfUrl = makeAbsoluteUrl("https://www.iprovest.com", hrefMatch[1]);
        }
      }

      if (pdfUrl) {
        try {
          var pdfResp = UrlFetchApp.fetch(pdfUrl, { headers: headers, muteHttpExceptions: true });
          if (pdfResp.getResponseCode() === 200 && pdfResp.getBlob().getBytes().length > 1000) {
            var blob = pdfResp.getBlob();
            blob.setName(fileName);
            saveFolder.createFile(blob);
            addFileToCache(folderCache, fileName);
            logFn("✅ [성공] " + fileName);
            count++;
          } else {
            if (fileDownMatch) {
              var altUrl = "https://www.iprovest.com/weblogic/RSReportServlet?action=download&filename=" + encodeURIComponent(fileDownMatch[2]);
              var altResp = UrlFetchApp.fetch(altUrl, { headers: headers, muteHttpExceptions: true });
              if (altResp.getResponseCode() === 200 && altResp.getBlob().getBytes().length > 1000) {
                var blob2 = altResp.getBlob();
                blob2.setName(fileName);
                saveFolder.createFile(blob2);
                addFileToCache(folderCache, fileName);
                logFn("✅ [성공] " + fileName);
                count++;
              }
            }
          }
        } catch (e) {
          logFn("❌ [다운로드 실패] " + fileName + ": " + e.toString());
        }
      }
    }
  } catch (e) {
    logFn("⚠️ 교보증권 접속/파싱 오류: " + e.toString());
  }

  logFn("✅ 교보증권 완료 (신규 " + count + "개 다운로드)\n");
  return count;
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
