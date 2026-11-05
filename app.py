import urllib.parse
import requests
import streamlit as st

GAS_WEB_APP_URL = st.secrets["GAS_WEB_APP_URL"]
GAS_API_KEY = st.secrets["GAS_API_KEY"]
SHEET_INCOME_ID = st.secrets["SHEET_INCOME_ID"]
SHEET_CATEGORY_ID = st.secrets["SHEET_CATEGORY_ID"]
SHEET_2026_JIGAI_ID = st.secrets["SHEET_2026_JIGAI_ID"]

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")


def call_gas(action, payload):
  payload["action"] = action
  payload["apiKey"] = GAS_API_KEY
  response = requests.post(GAS_WEB_APP_URL, json=payload)
  return response.json()


st.set_page_config(page_title="龍天宮 正月祭改報名系統", page_icon="⛩️")
st.title("⛩️ 龍天宮 民國116(2027)年 正月祭改快速報名")

if "matched_addresses" not in st.session_state:
  st.session_state.matched_addresses = []
if "selected_address" not in st.session_state:
  st.session_state.selected_address = None
if "people_list" not in st.session_state:
  st.session_state.people_list = []
if "search_done" not in st.session_state:
  st.session_state.search_done = False
if "submission_result" not in st.session_state:
  st.session_state.submission_result = None

# 規則 1：輸入姓名帶出地址
input_name = st.text_input("請輸入姓名查詢：", placeholder="例如：張一")

if st.button("查詢歷史地址"):
  if input_name.strip():
    with st.spinner("查詢中..."):
      res = call_gas(
          "search_jigai_2026",
          {"sheetId": SHEET_2026_JIGAI_ID, "name": input_name.strip()},
      )

      if res.get("status") == "success":
        addresses = res.get("addresses", [])
        st.session_state.matched_addresses = addresses
        st.session_state.search_done = True
        st.session_state.selected_address = None
        st.session_state.people_list = []
        st.session_state.submission_result = None

        if not addresses:
          st.error(
              "⚠️ 去年未參與祭改，請直接回原報名連結進行填寫"
          )
      else:
        st.error("查詢失敗，請檢查系統連結與 secrets 設定。")

if st.session_state.search_done and st.session_state.matched_addresses:
  st.success(
      f"找到 {len(st.session_state.matched_addresses)} 個相關地址，請點擊確認地址："
  )

  for idx, addr in enumerate(st.session_state.matched_addresses):
    if st.button(f"📍 確認地址：{addr}", key=f"addr_btn_{idx}"):
      st.session_state.selected_address = addr
      with st.spinner("載入該住址名單..."):
        people_res = call_gas(
            "search_jigai_2026",
            {"sheetId": SHEET_2026_JIGAI_ID, "address": addr},
        )
        if people_res.get("status") == "success":
          st.session_state.people_list = [
              p["name"] for p in people_res.get("people", [])
          ]

# 規則 2：勾選 116年(2027年) 祭改與計算金額
if st.session_state.selected_address and st.session_state.people_list:
  st.markdown("---")
  st.write(f"**確認地址：** {st.session_state.selected_address}")
  st.write(
      f"**同住址 2026 年參加名單（共 {len(st.session_state.people_list)} 人）：**"
      f" {', '.join(st.session_state.people_list)}"
  )

  jigai_checkbox = st.checkbox("☑️ 參加 116年(2027年)祭改")

  if jigai_checkbox:
    count = len(st.session_state.people_list)
    unit_price = 300
    total_amount = count * unit_price

    summary_text = f"116年(2027年)祭改人數 {count} 人金額為 {total_amount} 元"
    st.info(f"💡 **報名統計：** {summary_text}")

    confirm_amount = st.checkbox("點擊確認金額無誤")

    if confirm_amount:
      if st.button("🚀 送出報名並產生繳費 QR Code"):
        with st.spinner("正在寫入收入表與發送 Telegram 通知..."):
          submit_res = call_gas(
              "submit_registration",
              {
                  "incomeSheetId": SHEET_INCOME_ID,
                  "address": st.session_state.selected_address,
                  "peopleNames": st.session_state.people_list,
                  "count": count,
                  "totalAmount": total_amount,
                  "telegramBotToken": TELEGRAM_BOT_TOKEN,
                  "telegramChatId": TELEGRAM_CHAT_ID,
              },
          )

          if submit_res.get("status") == "success":
            st.session_state.submission_result = submit_res
            st.session_state.submission_result["count"] = count
            st.session_state.submission_result["totalAmount"] = total_amount
          else:
            st.error("報名失敗，請稍後再試。")

if st.session_state.submission_result:
  res = st.session_state.submission_result
  receipt_no = res.get("receiptNo")
  qr_code_url = res.get("qrCodeUrl")
  count = res.get("count")
  total_amount = res.get("totalAmount")

  st.success("🎉 報名資料已成功寫入收入表！")

  st.warning(
      f"⚠️ 繳款時請提供收據編號 (`{receipt_no}`) 或出示下方 QR code 連結。"
  )
  st.image(qr_code_url, caption="繳款 QR Code", width=220)

  line_text = (
      f"【龍天宮 116(2027)年 正月祭改報名】\n"
      f"收據編號：{receipt_no}\n"
      f"地址：{st.session_state.selected_address}\n"
      f"報名人員：{', '.join(st.session_state.people_list)}\n"
      f"116年(2027年)祭改人數 {count} 人金額為 {total_amount} 元\n\n"
      f"繳款 QR Code 連結：\n{qr_code_url}"
  )

  encoded_msg = urllib.parse.quote(line_text)
  line_url = f"https://line.me/R/oaMessage/@813bpsag/?{encoded_msg}"

  st.markdown("---")
  st.link_button("📱 點此打開 LINE 自動發送報名訊息", line_url)