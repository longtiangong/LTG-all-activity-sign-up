const CONFIG = {
  API_KEY: PropertiesService.getScriptProperties().getProperty("GAS_API_KEY") || "your-custom-secret-key"
};

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    // API KEY 驗證
    if (data.apiKey !== CONFIG.API_KEY) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "Unauthorized" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const action = data.action;

    // 1. 查詢 2026 祭改名單 (依姓名查詢地址，或依地址查詢同住址名單)
    if (action === "search_jigai_2026") {
      const sheetId = data.sheetId;
      const ss = SpreadsheetApp.openById(sheetId);
      const sheet = ss.getActiveSheet();
      const rows = sheet.getDataRange().getValues();
      
      const searchName = data.name;
      const searchAddress = data.address;
      
      if (searchName) {
        // 尋找符合姓名的地址列表
        const matchedAddresses = [];
        for (let i = 1; i < rows.length; i++) {
          const name = rows[i][0]; // 假設 A 欄為姓名
          const addr = rows[i][1]; // 假設 B 欄為地址
          if (name === searchName && addr) {
            if (!matchedAddresses.includes(addr)) {
              matchedAddresses.push(addr);
            }
          }
        }
        return responseJSON({ status: "success", addresses: matchedAddresses });
      } 
      else if (searchAddress) {
        // 尋找符合地址的所有成員名單
        const matchedPeople = [];
        for (let i = 1; i < rows.length; i++) {
          const name = rows[i][0];
          const addr = rows[i][1];
          if (addr === searchAddress) {
            matchedPeople.push({ name: name, address: addr });
          }
        }
        return responseJSON({ status: "success", people: matchedPeople });
      }
    }

    // 2. 獲取科目金額
    if (action === "get_category_price") {
      const sheetId = data.sheetId;
      const categoryName = data.categoryName; // 例："116年祭改"
      const ss = SpreadsheetApp.openById(sheetId);
      const sheet = ss.getActiveSheet();
      const rows = sheet.getDataRange().getValues();
      
      let price = 300; // 預設單價
      for (let i = 1; i < rows.length; i++) {
        if (rows[i][0] === categoryName) {
          price = Number(rows[i][1]);
          break;
        }
      }
      return responseJSON({ status: "success", price: price });
    }

    // 3. 提交報名：寫入收入表與推播 LINE 訊息
    if (action === "submit_registration") {
      const receiptNo = "RC" + new Date().getTime();
      const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(receiptNo)}`;
      
      // A. 寫入收入表 Sheet
      const incomeSheet = SpreadsheetApp.openById(data.incomeSheetId).getActiveSheet();
      incomeSheet.appendRow([
        new Date(),
        receiptNo,
        data.address,
        data.peopleNames.join(", "),
        data.count,
        data.totalAmount,
        qrCodeUrl,
        "未繳費"
      ]);

      // B. 發送 LINE 官方帳號訊息
      const lineMsg = `【法會報名成功通知】\n` +
                      `收據編號：${receiptNo}\n` +
                      `項目：116年(2027年)祭改\n` +
                      `地址：${data.address}\n` +
                      `報名人員：${data.peopleNames.join(", ")}\n` +
                      `116年(2027年)祭改人數 ${data.count} 人，金額為 ${data.totalAmount} 元\n\n` +
                      `請憑下方 QR Code 連結或提供收據編號進行繳款：\n${qrCodeUrl}`;
                      
      sendLineMessage(data.lineToken, data.lineUserId, lineMsg);

      return responseJSON({
        status: "success",
        receiptNo: receiptNo,
        qrCodeUrl: qrCodeUrl,
        message: `116年(2027年)祭改人數${data.count}人金額為${data.totalAmount}元`
      });
    }

  } catch (err) {
    return responseJSON({ status: "error", message: err.toString() });
  }
}

function sendLineMessage(token, userId, messageText) {
  const url = "https://api.line.me/v2/bot/message/push";
  const payload = {
    to: userId,
    messages: [{ type: "text", text: messageText }]
  };
  UrlFetchApp.fetch(url, {
    method: "post",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + token
    },
    payload: JSON.stringify(payload)
  });
}

function responseJSON(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}