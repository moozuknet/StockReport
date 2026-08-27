/**
 * NaverCollector.gs - 네이버 증권 5개 카테고리 수집기
 * (기업분석, 산업분석, 경제분석, 시장분석, 투자정보)
 */

var NAVER_CATEGORIES = [
  { sub_url: "company_list.naver", config_key: "네이버_기업분석", display_name: "기업분석" },
  { sub_url: "industry_list.naver", config_key: "네이버_산업분석", display_name: "산업분석" },
  { sub_url: "economy_list.naver", config_key: "네이버_경제분석", display_name: "경제분석" },
  { sub_url: "market_info_list.naver", config_key: "네이버_시장분석", display_name: "시장분석" },
  { sub_url: "invest_list.naver", config_key: "네이버_투자정보", display_name: "투자정보" }
];

function fetchNaverCategory(catInfo, saveFolder, targetDt, logFn, maxPages, folderCache) {
  if (maxPages === undefined) maxPages = 20;

  var naverDateStr = Utilities.formatDate(targetDt, "Asia/Seoul", "yy.MM.dd");
  logFn("🔍 > [네이버 " + catInfo.display_name + "] 탐색 시작 (" + naverDateStr + ")...");

  var baseUrl = "https://finance.naver.com/research/" + catInfo.sub_url;
  var userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
  var fetchOptions = {
    headers: {
      "User-Agent": userAgent,
      "Referer": "https://finance.naver.com/research/"
    },
    muteHttpExceptions: true
  };

  var downloadCount = 0;

  for (var page = 1; page <= maxPages; page++) {
    if (typeof isStopRequested === "function" && isStopRequested()) {
      logFn("🛑 [네이버 " + catInfo.display_name + "] 강제 중단됨.");
      return downloadCount;
    }

    try {
      var pageUrl = baseUrl + "?page=" + page;
      var response = UrlFetchApp.fetch(pageUrl, fetchOptions);
      if (response.getResponseCode() !== 200) break;

      var html = response.getContentText("euc-kr");
      var trMatches = html.match(/<tr[\s\S]*?<\/tr>/gi);
      if (!trMatches || trMatches.length === 0) break;

      var foundToday = false;

      for (var i = 0; i < trMatches.length; i++) {
        if (typeof isStopRequested === "function" && isStopRequested()) {
          logFn("🛑 [네이버 " + catInfo.display_name + "] 강제 중단됨.");
          return downloadCount;
        }

        var trHtml = trMatches[i];

        var dateMatch = trHtml.match(/\b(\d{2}\.\d{2}\.\d{2})\b/);
        if (!dateMatch) continue;

        var rowDate = dateMatch[1];
        if (rowDate !== naverDateStr) continue;

        foundToday = true;

        var tdMatches = trHtml.match(/<td[\s\S]*?<\/td>/gi);
        if (!tdMatches || tdMatches.length < 3) continue;

        var prefix = "";
        var title = "";
        var detailHref = "";
        var pdfHref = "";

        if (catInfo.display_name === "기업분석") {
          var prefixMatch = tdMatches[0].match(/<a[^>]*>([\s\S]*?)<\/a>/i);
          prefix = prefixMatch ? stripTags(prefixMatch[1]) : "기업";

          var titleMatch = tdMatches[1].match(/<a[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i);
          if (titleMatch) {
            detailHref = titleMatch[1];
            title = stripTags(titleMatch[2]);
            var titleAttrMatch = titleMatch[0].match(/title=["']([^"']+)["']/i);
            if (titleAttrMatch && titleAttrMatch[1].trim()) {
              title = titleAttrMatch[1].trim();
            }
          }
        } else if (catInfo.display_name === "산업분석") {
          prefix = stripTags(tdMatches[0]) || "산업";

          var titleMatch = tdMatches[1].match(/<a[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i);
          if (titleMatch) {
            detailHref = titleMatch[1];
            title = stripTags(titleMatch[2]);
            var titleAttrMatch = titleMatch[0].match(/title=["']([^"']+)["']/i);
            if (titleAttrMatch && titleAttrMatch[1].trim()) {
              title = titleAttrMatch[1].trim();
            }
          }
        } else {
          prefix = catInfo.display_name.replace("분석", "");
          var titleMatch = tdMatches[0].match(/<a[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i);
          if (titleMatch) {
            detailHref = titleMatch[1];
            title = stripTags(titleMatch[2]);
            var titleAttrMatch = titleMatch[0].match(/title=["']([^"']+)["']/i);
            if (titleAttrMatch && titleAttrMatch[1].trim()) {
              title = titleAttrMatch[1].trim();
            }
          }
        }

        var pdfMatch = trHtml.match(/<a[^>]*href=["']([^"']+\.pdf)["']/i);
        if (pdfMatch) {
          pdfHref = pdfMatch[1];
        }

        if (!title || !pdfHref) continue;

        var preliminaryFileName = cleanFilename("[" + prefix + "] " + title + ".pdf");
        var quickCheck = isSkipTarget(folderCache, preliminaryFileName, 0.90);
        if (quickCheck.skip) {
          logFn(quickCheck.isSimilar ? "📁 [유사 스킵] " + preliminaryFileName : "📁 [스킵] " + preliminaryFileName);
          continue;
        }

        if (title.endsWith("..") || title.endsWith("...")) {
          if (detailHref) {
            try {
              var detailUrl = makeAbsoluteUrl("https://finance.naver.com/research/", detailHref);
              var detailResp = UrlFetchApp.fetch(detailUrl, fetchOptions);
              if (detailResp.getResponseCode() === 200) {
                var detailHtml = detailResp.getContentText("euc-kr");
                var sbjMatch = detailHtml.match(/<(th|td|div|span)[^>]*class=["'][^"']*view_sbj[^"']*["'][^>]*>([\s\S]*?)<\/\1>/i);
                if (sbjMatch) {
                  var rawDetailTitle = stripTags(sbjMatch[2]);
                  rawDetailTitle = rawDetailTitle.replace(/\|\s*\d{2,4}\.\d{2}\.\d{2}[\s\S]*/, "").trim();
                  if (rawDetailTitle) title = rawDetailTitle;
                }
              }
            } catch (e) {
              logFn("⚠️ [네이버 상세 파싱 예외] " + e.toString());
            }
          }
        }

        var rawFileName = "[" + prefix + "] " + title + ".pdf";
        var fileName = cleanFilename(rawFileName);

        var check = isSkipTarget(folderCache, fileName, 0.95);
        if (check.skip) {
          logFn(check.isSimilar ? "📁 [유사 스킵(95%+)] " + fileName : "📁 [스킵] " + fileName);
          continue;
        }

        var pdfUrl = makeAbsoluteUrl("https://finance.naver.com/research/", pdfHref);
        try {
          var pdfResp = UrlFetchApp.fetch(pdfUrl, fetchOptions);
          if (pdfResp.getResponseCode() === 200) {
            var blob = pdfResp.getBlob();
            if (blob.getBytes().length > 1000) {
              blob.setName(fileName);
              saveFolder.createFile(blob);
              addFileToCache(folderCache, fileName);
              logFn("✅ [성공] " + fileName);
              downloadCount++;
            }
          }
        } catch (e) {
          logFn("❌ [다운로드 실패] " + fileName + ": " + e.toString());
        }
      }

      if (!foundToday) break;
    } catch (e) {
      logFn("⚠️ 네이버 " + catInfo.display_name + " 수집 오류: " + e.toString());
      break;
    }
  }

  logFn("✅ 네이버 " + catInfo.display_name + " 완료 (신규 " + downloadCount + "개 다운로드)");
  return downloadCount;
}

function stripTags(htmlStr) {
  if (!htmlStr) return "";
  return htmlStr.replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').trim();
}

function makeAbsoluteUrl(base, relative) {
  if (!relative) return base;
  if (relative.startsWith("http://") || relative.startsWith("https://")) return relative;
  if (relative.startsWith("/")) {
    var parts = base.split("/");
    return parts[0] + "//" + parts[2] + relative;
  }
  return base.replace(/\/[^\/]*$/, "/") + relative;
}
