/**
 * TelegramUtils.gs - Telegram Bot 알림 전송 모듈
 */

function sendTelegramMessage(token, chatId, htmlMessage) {
  if (!token || !chatId) {
    return { success: false, error: "토큰 또는 Chat ID가 설정되지 않았습니다." };
  }

  var url = "https://api.telegram.org/bot" + token + "/sendMessage";
  var payload = {
    chat_id: chatId,
    text: htmlMessage,
    parse_mode: "HTML",
    disable_web_page_preview: true
  };

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    var content = response.getContentText();

    if (code === 200) {
      return { success: true };
    } else {
      return { success: false, error: "HTTP " + code + ": " + content };
    }
  } catch (e) {
    return { success: false, error: e.toString() };
  }
}
