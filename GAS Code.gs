const CONFIG = {
  API_KEY: PropertiesService.getScriptProperties().getProperty("GAS_API_KEY") || "your-custom-secret-key"
};

function formatDateTime(date) {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`;
}

function formatDate(date) {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    if (data.apiKey !== CONFIG.API_KEY) {
      return responseJSON({ status: "error", message: "Unauthorized" });
    }

    const action = data.action;

    // # * 11051310 更改欄位
    // 1. 查詢指定分頁的祭改名單：姓名 D 欄、住址 B 欄
    if (action === "search_jigai_2026") {
      const sheetId = data.sheetId;
      const ss = SpreadsheetApp.openById(sheetId);
      const sheetName = "2026年正月祭改";
      const sheet = ss.getSheetByName(sheetName);
      if (!sheet) {
        return responseJSON({
          status: "error",
          message: `找不到工作表分頁「${sheetName}」`
        });
      }
      const rows = sheet.getDataRange().getValues();
      
      const searchName = data.name;
      const searchAddress = data.address;
      
      if (searchName) {
        const matchedAddresses = [];
        for (let i = 1; i < rows.length; i++) {
          const addr = String(rows[i][1]).trim();
          const name = String(rows[i][3]).trim();
          if (name === searchName && addr) {
            if (!matchedAddresses.includes(addr)) {
              matchedAddresses.push(addr);
            }
          }
        }
        return responseJSON({ status: "success", addresses: matchedAddresses });
      } 
      else if (searchAddress) {
        const matchedPeople = [];
        for (let i = 1; i < rows.length; i++) {
          const addr = String(rows[i][1]).trim();
          const name = String(rows[i][3]).trim();
          if (addr === searchAddress) {
            matchedPeople.push({ name: name, address: addr });
          }
        }
        return responseJSON({ status: "success", people: matchedPeople });
      }
    }

    // 2. 寫入收入表與推播 Telegram
    if (action === "submit_registration") {
      const now = new Date();
      const timestamp = now.getTime();
      
      const datePrefix = formatDate(now).replace(/-/g, "");
      const receiptNo = `LTG-${datePrefix}-${String(timestamp).slice(-3)}`;
      
      const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(receiptNo)}`;
      
      const incomeSheet = SpreadsheetApp.openById(data.incomeSheetId).getActiveSheet();
      
      const primaryName = data.peopleNames && data.peopleNames.length > 0 ? data.peopleNames[0] : "";
      const systemNote = `祭改祭改人數${data.count}人金額為${data.totalAmount}元`;
      
      incomeSheet.appendRow([
        receiptNo,                   // A: 收據編號
        formatDateTime(now),         // B: 開立時間
        primaryName,                 // C: 姓名
        data.address,                // D: 地址
        "收入",                       // E: 辦理項目
        "祭改",                       // F: 科目
        "祭改",                       // G: 規格
        data.totalAmount,            // H: 金額(元)
        data.count,                  // I: 選項人數
        systemNote,                  // J: 系統備註
        "已收",                       // K: 經手人備註
        qrCodeUrl,                   // L: PDF連結/QR連結
        formatDate(now),             // M: 收入日期
        "LTG官方Line"                // N: 經手人
      ]);

      const notifyMsg = `【龍天宮 116(2027)年 正月祭改報名通知】\n` +
                        `收據編號：${receiptNo}\n` +
                        `姓名代表：${primaryName}\n` +
                        `地址：${data.address}\n` +
                        `報名人員：${data.peopleNames.join(", ")}\n` +
                        `116年(2027年)祭改人數 ${data.count} 人，金額為 ${data.totalAmount} 元\n\n` +
                        `QR Code 連結：\n${qrCodeUrl}`;

      if (data.telegramBotToken && data.telegramChatId) {
        sendTelegramMessage(data.telegramBotToken, data.telegramChatId, notifyMsg);
      }

      return responseJSON({
        status: "success",
        receiptNo: receiptNo,
        openedAt: formatDateTime(now),
        qrCodeUrl: qrCodeUrl,
        message: `116年(2027年)祭改人數${data.count}人金額為${data.totalAmount}元`
      });
    }

    // # * 11051406 更改PDF放的路徑
    if (action === "save_registration_pdf") {
      if (!data.folderId) {
        return responseJSON({
          status: "error",
          message: "未設定收執聯與存根聯 PDF 資料夾 ID"
        });
      }

      const sheet = SpreadsheetApp.openById(data.incomeSheetId)
        .getActiveSheet();
      const receiptCell = sheet.getRange("A:A")
        .createTextFinder(String(data.receiptNo))
        .matchEntireCell(true)
        .findNext();
      if (!receiptCell) {
        return responseJSON({
          status: "error",
          message: `收入表找不到收據編號「${data.receiptNo}」`
        });
      }

      const pdfBlob = Utilities.newBlob(
        Utilities.base64Decode(data.pdfBase64),
        "application/pdf",
        `${data.receiptNo}.pdf`
      );
      const pdfFolder = DriveApp.getFolderById(String(data.folderId));
      const pdfFile = pdfFolder.createFile(pdfBlob);
      pdfFile.setSharing(
        DriveApp.Access.ANYONE_WITH_LINK,
        DriveApp.Permission.VIEW
      );
      sheet.getRange(receiptCell.getRow(), 12).setValue(pdfFile.getUrl());
      PropertiesService.getScriptProperties().setProperty(
        "SHEET_INCOME_ID",
        data.incomeSheetId
      );

      return responseJSON({
        status: "success",
        pdfUrl: pdfFile.getUrl()
      });
    }

  } catch (err) {
    return responseJSON({ status: "error", message: err.toString() });
  }
}

function doGet(e) {
  const receiptNo = e && e.parameter ? e.parameter.receipt : "";
  const incomeSheetId = PropertiesService.getScriptProperties()
    .getProperty("SHEET_INCOME_ID");
  if (!receiptNo || !incomeSheetId) {
    return HtmlService.createHtmlOutput("找不到此收據。");
  }

  try {
    const sheet = SpreadsheetApp.openById(incomeSheetId).getActiveSheet();
    const receiptCell = sheet.getRange("A:A")
      .createTextFinder(String(receiptNo))
      .matchEntireCell(true)
      .findNext();
    const pdfUrl = receiptCell
      ? sheet.getRange(receiptCell.getRow(), 12).getValue()
      : "";
    if (!pdfUrl) {
      return HtmlService.createHtmlOutput("找不到此收據 PDF。");
    }

    return HtmlService.createHtmlOutput(
      `<p>龍天宮收據已建立：<a href="${htmlEscape(pdfUrl)}">開啟 PDF</a></p>`
    );
  } catch (err) {
    return HtmlService.createHtmlOutput(
      `讀取收據失敗：${htmlEscape(err.toString())}`
    );
  }
}

function authorizeReceiptDriveAccess() {
  const folder = DriveApp.getRootFolder();
  console.log(`Google Drive access authorized: ${folder.getName()}`);
}

function htmlEscape(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[character]));
}

function sendTelegramMessage(botToken, chatId, messageText) {
  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  const payload = {
    chat_id: chatId,
    text: messageText
  };
  UrlFetchApp.fetch(url, {
    method: "post",
    headers: {
      "Content-Type": "application/json"
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
}

function responseJSON(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}