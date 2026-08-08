/**
 * DriveUtils.gs - 구글 드라이브 스마트 탐색, 파일 처리 및 PDF/DOC 요약집 폴더 관리 모듈
 */

function getOrCreateFolder(folderName, parentFolder) {
  var parent = parentFolder || DriveApp.getRootFolder();
  var folders = parent.getFoldersByName(folderName);
  if (folders.hasNext()) {
    return folders.next();
  } else {
    return parent.createFolder(folderName);
  }
}

function extractFolderId(inputStr) {
  if (!inputStr) return "";
  var trimmed = inputStr.trim();
  var match = trimmed.match(/\/folders\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  return trimmed;
}

function getEffectiveSaveFolder(config, targetDate, createIfMissing) {
  var rootFolder = null;

  if (config.save_folder_id && config.save_folder_id.trim() !== "") {
    var folderId = extractFolderId(config.save_folder_id);
    try {
      rootFolder = DriveApp.getFolderById(folderId);
    } catch (e) {
      Logger.log("⚠️ 저장 폴더 ID(" + folderId + ") 조회 실패. 기본 폴더명으로 대체합니다: " + e.toString());
    }
  }

  if (!rootFolder) {
    var rootFolderName = config.save_folder_name || "증권사별리포트";
    rootFolder = getOrCreateFolder(rootFolderName);
  }

  if (config.use_date_folder && targetDate) {
    var dateStr = Utilities.formatDate(targetDate, "Asia/Seoul", "yyyy-MM-dd");
    var existingFolders = rootFolder.getFoldersByName(dateStr);
    if (existingFolders.hasNext()) {
      return existingFolders.next();
    } else {
      if (createIfMissing === true) {
        return rootFolder.createFolder(dateStr);
      } else {
        return null;
      }
    }
  }

  return rootFolder;
}

/**
 * ⚡ [지연 생성 폴더 프록시] 리포트 파일이 실제로 다운로드될 때만 일자별 폴더(YYYY-MM-DD)를 지연 생성
 */
function getSaveFolderProxy(config, targetDate) {
  var existing = getEffectiveSaveFolder(config, targetDate, false);
  if (existing) return existing;

  return {
    isProxy: true,
    realFolder: null,
    getRealFolder: function() {
      if (!this.realFolder) {
        this.realFolder = getEffectiveSaveFolder(config, targetDate, true);
      }
      return this.realFolder;
    },
    getName: function() {
      if (targetDate) {
        return Utilities.formatDate(targetDate, "Asia/Seoul", "yyyy-MM-dd");
      }
      return "증권사별리포트";
    },
    createFile: function(blob) {
      return this.getRealFolder().createFile(blob);
    },
    getFilesByName: function(name) {
      var f = this.realFolder || getEffectiveSaveFolder(config, targetDate, false);
      return f ? f.getFilesByName(name) : DriveApp.getRootFolder().getFilesByName("NON_EXISTENT_FILE_XYZ");
    },
    getFiles: function() {
      var f = this.realFolder || getEffectiveSaveFolder(config, targetDate, false);
      return f ? f.getFiles() : DriveApp.getRootFolder().getFilesByName("NON_EXISTENT_FILE_XYZ");
    }
  };
}

/**
 * 🔍 초강력 글로벌 PDF 파일 검색: 지정 일자의 PDF 리포트를 모든 하위 폴더 및 전역 드라이브에서 100% 탐색
 */
function findAllPdfFilesForDate(config, targetDate, logFn) {
  var dateStr = Utilities.formatDate(targetDate, "Asia/Seoul", "yyyy-MM-dd");
  var compactDateStr = dateStr.replace(/-/g, "");
  var pdfFiles = [];
  var fileIdMap = {};

  function addPdf(file) {
    if (file && file.getName().toLowerCase().endsWith(".pdf") && !fileIdMap[file.getId()]) {
      fileIdMap[file.getId()] = true;
      pdfFiles.push(file);
    }
  }

  var dateFolder = getEffectiveSaveFolder(config, targetDate);
  var files = dateFolder.getFiles();
  while (files.hasNext()) {
    addPdf(files.next());
  }

  if (pdfFiles.length > 0) {
    if (logFn) logFn("📁 [폴더 감지] '" + dateFolder.getName() + "' 폴더에서 총 " + pdfFiles.length + "개 PDF 리포트를 발견했습니다.");
    return { folder: dateFolder, files: pdfFiles };
  }

  var rootFolder = getEffectiveSaveFolder(config, null);
  files = rootFolder.getFiles();
  while (files.hasNext()) {
    addPdf(files.next());
  }

  if (pdfFiles.length > 0) {
    if (logFn) logFn("📁 [폴더 감지] 루트 저장 폴더('" + rootFolder.getName() + "')에서 총 " + pdfFiles.length + "개 PDF 리포트를 발견했습니다.");
    return { folder: rootFolder, files: pdfFiles };
  }

  try {
    var targetFolders = DriveApp.getFoldersByName(dateStr);
    while (targetFolders.hasNext()) {
      var tf = targetFolders.next();
      var tfFiles = tf.getFiles();
      while (tfFiles.hasNext()) {
        addPdf(tfFiles.next());
      }
      if (pdfFiles.length > 0) {
        if (logFn) logFn("📁 [폴더 감지] 드라이브 폴더('" + tf.getName() + "')에서 총 " + pdfFiles.length + "개 PDF 리포트를 발견했습니다.");
        return { folder: tf, files: pdfFiles };
      }
    }
  } catch (e) {
    // ignore
  }

  try {
    var searchQuery = "title contains '.pdf' and (title contains '" + dateStr + "' or title contains '" + compactDateStr + "')";
    var searchedFiles = DriveApp.searchFiles(searchQuery);
    while (searchedFiles.hasNext()) {
      addPdf(searchedFiles.next());
    }
    if (pdfFiles.length > 0) {
      if (logFn) logFn("📁 [전역 감지] 구글 드라이브 전체에서 해당 일자의 PDF 리포트 " + pdfFiles.length + "개를 발견했습니다.");
      return { folder: rootFolder, files: pdfFiles };
    }
  } catch (e) {
    // ignore
  }

  return { folder: dateFolder, files: [] };
}

/**
 * 📂 요약집 전용 구글 드라이브 폴더 반환
 */
function getOrCreateSummaryFolder(config) {
  var summaryFolder = null;

  if (config.summary_folder_id && config.summary_folder_id.trim() !== "") {
    var folderId = extractFolderId(config.summary_folder_id);
    try {
      summaryFolder = DriveApp.getFolderById(folderId);
    } catch (e) {
      Logger.log("⚠️ 요약 폴더 ID(" + folderId + ") 조회 실패. 폴더명으로 새로 검색/생성합니다: " + e.toString());
    }
  }

  if (!summaryFolder) {
    var folderName = config.summary_folder_name || "증권리포트_요약집";
    summaryFolder = getOrCreateSummaryFolderByName(folderName);
  }

  return summaryFolder;
}

function getOrCreateSummaryFolderByName(folderName) {
  var root = DriveApp.getRootFolder();
  var folders = root.getFoldersByName(folderName);
  if (folders.hasNext()) {
    return folders.next();
  } else {
    return root.createFolder(folderName);
  }
}

/**
 * 🏷️ 파일명 기반 5대 카테고리/섹션 정밀 분류 엔진
 */
function classifyReportSector(filename) {
  if (typeof parseReportFilename === "function") {
    try {
      var res = parseReportFilename(filename);
      if (res && res.sector) return res.sector;
    } catch (e) {}
  }

  var nameNoExt = filename.replace(/\.pdf$/i, "").trim();
  var bracketMatch = nameNoExt.match(/^\[([^\]]+)\]\s*(.*)$/);

  if (bracketMatch) {
    var tag = bracketMatch[1].trim().toLowerCase();
    if (tag.indexOf("산업") !== -1 || tag.indexOf("업종") !== -1) return "산업/업종";
    if (tag.indexOf("경제") !== -1 || tag.indexOf("macro") !== -1) return "거시경제";
    if (tag.indexOf("시장") !== -1 || tag.indexOf("시황") !== -1 || tag.indexOf("전략") !== -1 || tag.indexOf("daily") !== -1) return "증시전략";
    if (tag.indexOf("투자") !== -1 || tag.indexOf("esg") !== -1 || tag.indexOf("insight") !== -1) return "투자정보";
    return "기업분석"; // 대괄호 안의 종목명([삼성전자], [SK하이닉스] 등)은 기업분석!
  }

  if (nameNoExt.indexOf("산업") !== -1 || nameNoExt.indexOf("반도체") !== -1 || nameNoExt.indexOf("바이오") !== -1 || nameNoExt.indexOf("자동차") !== -1) return "산업/업종";
  if (nameNoExt.indexOf("경제") !== -1 || nameNoExt.indexOf("달러") !== -1 || nameNoExt.indexOf("금리") !== -1) return "거시경제";
  if (nameNoExt.indexOf("증시") !== -1 || nameNoExt.indexOf("시황") !== -1 || nameNoExt.indexOf("전략") !== -1) return "증시전략";

  return "투자정보";
}

/**
 * ⚡ [달력 인덱스 실시간 업데이터] 구글 드라이브 일별 폴더 내 PDF 파일 전수 분류 및 섹션/카테고리 매핑 갱신
 */
function refreshCalendarIndexCache(config) {
  if (!config) config = getConfig();
  var summaryFolder = getOrCreateSummaryFolder(config);
  var rootSaveFolder = getEffectiveSaveFolder(config, null);

  var summaryMap = {};
  var folderMap = {};

  // 1. 요약집 PDF & DOC 파일 100% 동시 매핑
  try {
    var files = summaryFolder.getFiles();

    while (files.hasNext()) {
      var file = files.next();
      var fileName = file.getName();
      var dateMatch = fileName.match(/(\d{4}-\d{2}-\d{2})/);
      if (dateMatch) {
        var dateKey = dateMatch[1];
        var updatedTime = file.getLastUpdated().getTime();
        var mimeType = file.getMimeType();
        var isPdf = fileName.toLowerCase().endsWith(".pdf") || mimeType === "application/pdf";
        var isDoc = mimeType === "application/vnd.google-apps.document";
        var isMd = fileName.toLowerCase().endsWith(".md") || mimeType === "text/markdown" || mimeType === "text/plain";

        if (!summaryMap[dateKey]) {
          summaryMap[dateKey] = {};
        }

        if (isPdf) {
          if (!summaryMap[dateKey].pdfTime || updatedTime > summaryMap[dateKey].pdfTime) {
            summaryMap[dateKey].name = fileName;
            summaryMap[dateKey].url = file.getUrl();
            summaryMap[dateKey].fileId = file.getId();
            summaryMap[dateKey].pdfTime = updatedTime;
            summaryMap[dateKey].isPdf = true;
          }
        }

        if (isMd || isDoc) {
          if (!summaryMap[dateKey].docTime || updatedTime > summaryMap[dateKey].docTime) {
            summaryMap[dateKey].docUrl = file.getUrl();
            summaryMap[dateKey].mdUrl = file.getUrl();
            summaryMap[dateKey].docId = file.getId();
            summaryMap[dateKey].docTime = updatedTime;
            summaryMap[dateKey].isMd = true;
          }
        }
      }
    }
  } catch (e) {
    Logger.log("⚠️ 요약집 캐시 인덱싱 오류: " + e.toString());
  }

  // 2. 수집 일별 하위 폴더 매핑 및 PDF 파일별 5대 섹션/카테고리 재분류 갱신
  try {
    var subFolders = rootSaveFolder.getFolders();
    while (subFolders.hasNext()) {
      var sf = subFolders.next();
      var sfName = sf.getName();
      var dateMatch = sfName.match(/(\d{4}-\d{2}-\d{2})/);
      if (dateMatch) {
        var dateKey = dateMatch[1];
        var sectorCounts = { "기업분석": 0, "산업/업종": 0, "거시경제": 0, "증시전략": 0, "투자정보": 0 };
        var totalCount = 0;

        var sfFiles = sf.getFiles();
        while (sfFiles.hasNext()) {
          var f = sfFiles.next();
          var fn = f.getName();
          if (fn.toLowerCase().endsWith(".pdf")) {
            totalCount++;
            var sec = classifyReportSector(fn);
            if (sectorCounts[sec] !== undefined) sectorCounts[sec]++;
            else sectorCounts["투자정보"]++;
          }
        }

        folderMap[dateKey] = {
          url: sf.getUrl(),
          id: sf.getId(),
          totalCount: totalCount,
          sectorCounts: sectorCounts
        };
      }
    }
  } catch (e) {
    Logger.log("⚠️ 일별 폴더 캐시 인덱싱 오류: " + e.toString());
  }

  var cacheData = {
    summaryMap: summaryMap,
    folderMap: folderMap,
    rootFolderUrl: rootSaveFolder.getUrl(),
    updatedAt: new Date().getTime()
  };

  try {
    var props = PropertiesService.getUserProperties();
    props.setProperty("CALENDAR_INDEX_CACHE", JSON.stringify(cacheData));
  } catch (e) {
    // ignore
  }

  return cacheData;
}

function getSummaryCalendarData(year, month, config) {
  if (!config) config = getConfig();
  return refreshCalendarIndexCache(config);
}

/**
 * ⚡ 폴더 내 기존 파일 목록 메모리 캐시 구축 함수
 */
function getFolderCache(folder) {
  var cache = {
    names: [],
    nameMap: {}
  };

  if (!folder) return cache;

  try {
    var files = folder.getFiles();
    while (files.hasNext()) {
      var f = files.next();
      var name = f.getName();
      cache.names.push(name);
      cache.nameMap[name] = f.getId();
    }
  } catch (e) {
    Logger.log("⚠️ getFolderCache 예외: " + e.toString());
  }

  return cache;
}

/**
 * ⚡ 파일 스킵 여부 검사 (중복 다운로드 100% 방지)
 */
function isSkipTarget(folderCache, fileName, threshold) {
  if (!folderCache || !folderCache.names || folderCache.names.length === 0) {
    return { skip: false };
  }

  var targetName = fileName ? fileName.trim() : "";
  if (!targetName) return { skip: false };

  if (folderCache.nameMap && folderCache.nameMap[targetName]) {
    return { skip: true, reason: "동일 파일명 존재" };
  }

  for (var i = 0; i < folderCache.names.length; i++) {
    var existing = folderCache.names[i];
    if (existing === targetName) {
      return { skip: true, reason: "동일 파일 존재" };
    }
  }

  return { skip: false };
}

/**
 * ⚡ 다운로드 완료 후 캐시에 새 파일 추가
 */
function addFileToCache(folderCache, fileName) {
  if (!folderCache || !fileName) return;
  if (!folderCache.names) folderCache.names = [];
  if (!folderCache.nameMap) folderCache.nameMap = {};

  var trimmed = fileName.trim();
  folderCache.names.push(trimmed);
  folderCache.nameMap[trimmed] = true;
}

/**
 * 🧹 파일명에서 윈도우/OS 금지 특수문자를 제거하고 다중 공백을 정돈합니다.
 */
function cleanFilename(filename) {
  if (!filename) return "";
  var cleaned = filename.replace(/[\\/*?:"<>|]/g, '');
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  return cleaned;
}

/**
 * 🧩 '종목명 (코드) 제목' 문장 패턴에서 종목명과 제목을 파싱합니다.
 */
function parseCompanyAndTitle(rawText) {
  if (!rawText) return { company: "", title: "" };
  var match = rawText.match(/^([^(]+)\s*\([^)]*\)\s*(.*)$/);
  if (match) {
    var company = match[1].trim();
    var title = match[2].trim();
    return { company: company, title: title };
  }
  return { company: "", title: rawText.trim() };
}
