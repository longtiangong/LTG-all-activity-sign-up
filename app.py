import base64
import datetime
import urllib.parse
import uuid

import requests
import streamlit as st

from receipt_pdf import create_receipt_pdf, create_receipt_qr

GAS_WEB_APP_URL = st.secrets["GAS_WEB_APP_URL"]
GAS_API_KEY = st.secrets["GAS_API_KEY"]
SHEET_INCOME_ID = st.secrets["SHEET_INCOME_ID"]
SHEET_CATEGORY_ID = st.secrets["SHEET_CATEGORY_ID"]
SHEET_2026_JIGAI_ID = st.secrets["SHEET_2026_JIGAI_ID"]
SHEET_BELIEVER_ID = str(st.secrets.get("SHEET_BELIEVER_ID", "")).strip()
# * 11051406 更改PDF放的路徑
RECEIPT_PDF_FOLDER_ID = str(
    st.secrets.get("RECEIPT_PDF_FOLDER_ID", "")
).strip()

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")


def call_gas(action, payload):
  payload["action"] = action
  payload["apiKey"] = GAS_API_KEY
  response = requests.post(GAS_WEB_APP_URL, json=payload, timeout=30)
  return response.json()


def build_receipt_qr_url(receipt_no):
  separator = "&" if "?" in GAS_WEB_APP_URL else "?"
  return (
      f"{GAS_WEB_APP_URL}{separator}"
      f"{urllib.parse.urlencode({'receipt': receipt_no})}"
  )


st.set_page_config(page_title="龍天宮 正月祭改報名系統", page_icon="⛩️")
st.title("⛩️ 龍天宮 民國116(2027)年 正月祭改快速報名")

if "matched_addresses" not in st.session_state:
  st.session_state.matched_addresses = []
if "matched_people" not in st.session_state:
  st.session_state.matched_people = []
if "selected_address" not in st.session_state:
  st.session_state.selected_address = None
if "people_list" not in st.session_state:
  st.session_state.people_list = []
if "search_done" not in st.session_state:
  st.session_state.search_done = False
if "verified_name" not in st.session_state:
  st.session_state.verified_name = None
if "last_year_participant" not in st.session_state:
  st.session_state.last_year_participant = False
if "submission_result" not in st.session_state:
  st.session_state.submission_result = None
if "people_selection_id" not in st.session_state:
  st.session_state.people_selection_id = uuid.uuid4().hex

# 規則 1：先確認去年是否參與，再以手機查詢信徒資料總表中的住址
input_name = st.text_input("請輸入姓名：", placeholder="例如：張一")

if st.button("確認是否去年有參加"):
  if input_name.strip():
    with st.spinner("查詢中..."):
      res = call_gas(
          "search_jigai_2026",
          {"sheetId": SHEET_2026_JIGAI_ID, "name": input_name.strip()},
      )

      if res.get("status") == "success":
        addresses = res.get("addresses", [])
        st.session_state.verified_name = input_name.strip()
        st.session_state.last_year_participant = bool(addresses)
        st.session_state.matched_addresses = []
        st.session_state.matched_people = []
        st.session_state.search_done = False
        st.session_state.selected_address = None
        st.session_state.people_list = []
        st.session_state.submission_result = None

        if not addresses:
          st.error(
              "⚠️ 查無去年參加紀錄，請直接回原報名連結進行填寫。"
          )
      else:
        error_message = res.get("message", "未知錯誤")
        st.error(f"查詢失敗：{error_message}")
  else:
    st.warning("請先輸入姓名。")

name_is_verified = (
    st.session_state.verified_name == input_name.strip()
    and st.session_state.last_year_participant
)

if name_is_verified:
  # * 11061214 再輸入手機號碼當個別密碼
  input_phone = st.text_input(
      "請輸入手機號碼（作為個別密碼）：",
      placeholder="請輸入信徒資料總表登記的手機號碼",
  )
  if st.button("驗證手機並查詢去年住址"):
    if not SHEET_BELIEVER_ID:
      st.error("請先在 Streamlit secrets 設定 SHEET_BELIEVER_ID。")
    elif input_phone.strip():
      with st.spinner("驗證信徒資料並查詢去年住址中..."):
        res = call_gas(
            "search_believer_address",
            {
                "believerSheetId": SHEET_BELIEVER_ID,
                "jigaiSheetId": SHEET_2026_JIGAI_ID,
                "name": st.session_state.verified_name,
                "phone": input_phone.strip(),
            },
        )

        if res.get("status") == "success":
          addresses = res.get("addresses", [])
          st.session_state.matched_addresses = addresses
          st.session_state.matched_people = res.get("people", [])
          st.session_state.search_done = True
          st.session_state.selected_address = None
          st.session_state.people_list = []
          st.session_state.submission_result = None

          if not addresses:
            st.warning(
                "查無符合的去年住址，請聯絡龍天宮小編建檔。"
            )
        else:
          error_message = res.get("message", "未知錯誤")
          st.error(f"驗證信徒資料或查詢去年住址失敗：{error_message}")
    else:
      st.warning("請先輸入手機號碼。")

if (
    name_is_verified
    and st.session_state.search_done
    and st.session_state.matched_addresses
):
  st.success(
      f"找到 {len(st.session_state.matched_addresses)} 個相關地址，請點擊確認地址："
  )

  for idx, addr in enumerate(st.session_state.matched_addresses):
    if st.button(f"📍 確認地址：{addr}", key=f"addr_btn_{idx}"):
      st.session_state.selected_address = addr
      st.session_state.people_selection_id = uuid.uuid4().hex
      st.session_state.people_list = st.session_state.matched_people
      st.session_state.submission_result = None

# # * 11051346 更改個別可選擇
# 規則 2：個別選擇參加 116 年（2027 年）祭改的人員
if (
    name_is_verified
    and st.session_state.selected_address
    and st.session_state.people_list
):
  st.markdown("---")
  st.write(f"**確認地址：** {st.session_state.selected_address}")
  st.write(
      f"**同手機關聯的 2026 年參加名單（共 {len(st.session_state.people_list)} 人），"
      "請勾選本次參加者：**"
  )
  st.caption(
      "名單會包含信徒資料總表中登記相同手機的姓名，即使去年住址不同；"
      "收據地址使用上方確認的地址。"
  )
  selected_indices = []
  for idx, person in enumerate(st.session_state.people_list):
    name = person["name"]
    addresses = "、".join(person.get("addresses", []))
    if st.checkbox(
        f"參加 116 年（2027 年）祭改：{name}（{addresses}）",
        key=f"jigai_person_{st.session_state.people_selection_id}_{idx}",
    ):
      selected_indices.append(idx)

  selected_people = [
      st.session_state.people_list[idx]["name"] for idx in selected_indices
  ]
  count = len(selected_people)
  unit_price = 300
  total_amount = count * unit_price

  if count:
    summary_text = f"116年(2027年)祭改人數 {count} 人金額共 {total_amount} 元"
    st.info(f"💡 **報名統計：** {summary_text}")

    confirm_key = (
        f"confirm_amount_{st.session_state.people_selection_id}_"
        f"{','.join(map(str, selected_indices))}"
    )
    confirm_amount = st.checkbox("點擊確認金額無誤", key=confirm_key)

    if confirm_amount:
      if st.button("🚀 送出報名並產生繳費 QR Code"):
        if not RECEIPT_PDF_FOLDER_ID:
          st.error(
              "請先在 secrets.toml 設定 RECEIPT_PDF_FOLDER_ID，"
              "填入「5.收執聯與存根聯」資料夾 ID。"
          )
        else:
          with st.spinner("正在寫入收入表、產生 PDF 並發送 Telegram 通知..."):
            submit_res = call_gas(
                "submit_registration",
                {
                    "incomeSheetId": SHEET_INCOME_ID,
                    "address": st.session_state.selected_address,
                    "peopleNames": selected_people,
                    "count": count,
                    "totalAmount": total_amount,
                },
            )

            if submit_res.get("status") == "success":
              receipt_no = submit_res["receiptNo"]
              issued_at = submit_res.get("openedAt") or datetime.datetime.now(
                  datetime.timezone(datetime.timedelta(hours=8))
              ).strftime("%Y-%m-%d %H:%M:%S")
              qr_url = build_receipt_qr_url(receipt_no)
              system_note = (
                  f"祭改祭改人數{count}人金額共{total_amount}元"
              )
              receipt_data = {
                  "收據編號": receipt_no,
                  "QR連結": qr_url,
                  "開立時間": issued_at,
                  "姓名": selected_people[0],
                  "地址": st.session_state.selected_address,
                  "辦理項目": "收入",
                  "收到金額": total_amount,
                  "科目": "祭改",
                  "規格": "祭改",
                  "選項人數": count,
                  "系統備註": system_note,
                  "經手人": "LTG官方Line",
                  "經手人備註": "祭改報名系統自動產生",
              }
              pdf_bytes = create_receipt_pdf(receipt_data)
              try:
                pdf_result = call_gas(
                    "save_registration_pdf",
                    {
                        "incomeSheetId": SHEET_INCOME_ID,
                        "receiptNo": receipt_no,
                        "folderId": RECEIPT_PDF_FOLDER_ID,
                        "pdfBase64": base64.b64encode(pdf_bytes).decode("ascii"),
                        "address": st.session_state.selected_address,
                        "peopleNames": selected_people,
                        "count": count,
                        "totalAmount": total_amount,
                        "telegramBotToken": TELEGRAM_BOT_TOKEN,
                        "telegramChatId": TELEGRAM_CHAT_ID,
                    },
                )
              except requests.RequestException as error:
                pdf_result = {
                    "status": "error",
                    "message": f"連線失敗：{error}",
                }
              except ValueError as error:
                pdf_result = {
                    "status": "error",
                    "message": f"GAS 回應格式錯誤：{error}",
                }
              st.session_state.submission_result = submit_res
              st.session_state.submission_result["count"] = count
              st.session_state.submission_result["totalAmount"] = total_amount
              st.session_state.submission_result["peopleNames"] = selected_people
              st.session_state.submission_result["pdfBytes"] = pdf_bytes
              if pdf_result.get("status") == "success":
                st.session_state.submission_result["pdfUrl"] = pdf_result.get(
                    "pdfUrl", ""
                )
                if pdf_result.get("telegramStatus") == "error":
                  st.session_state.submission_result["telegramError"] = (
                      pdf_result.get("telegramError", "未知錯誤")
                  )
              else:
                st.session_state.submission_result["pdfError"] = pdf_result.get(
                    "message", "未知錯誤"
                )
            else:
              error_message = submit_res.get("message", "未知錯誤")
              st.error(f"報名失敗：{error_message}")
  else:
    st.caption("請至少勾選一位參加者。")

if name_is_verified and st.session_state.submission_result:
  res = st.session_state.submission_result
  receipt_no = res.get("receiptNo")
  count = res.get("count")
  total_amount = res.get("totalAmount")
  people_names = res.get("peopleNames", [])
  pdf_bytes = res.get("pdfBytes")
  pdf_url = res.get("pdfUrl")

  st.success("🎉 報名資料已成功寫入收入表！")

  st.warning(
      f"⚠️ 繳款時請提供收據編號 (`{receipt_no}`) 或出示下方 QR code 連結。"
  )
  st.image(
      create_receipt_qr(build_receipt_qr_url(receipt_no)),
      caption="掃描 QR Code 開啟收據 PDF",
      width=220,
  )
  if pdf_bytes:
    st.download_button(
        "下載收執聯／存根聯 PDF",
        data=pdf_bytes,
        file_name=f"{receipt_no}.pdf",
        mime="application/pdf",
    )
  if pdf_url:
    st.link_button("開啟線上收據 PDF", pdf_url)
    if res.get("telegramError"):
      st.warning(f"PDF 已建立，但 Telegram 通知失敗：{res['telegramError']}")
  else:
    st.error(
        "報名已寫入，但 PDF 上傳至 Google Drive 失敗："
        f"{res.get('pdfError', '未知錯誤')}"
    )

  line_text = (
      f"【龍天宮 116(2027)年 正月祭改報名】\n"
      f"收據編號：{receipt_no}\n"
      f"地址：{st.session_state.selected_address}\n"
      f"報名人員：{', '.join(people_names)}\n"
      f"116年(2027年)祭改人數 {count} 人金額共 {total_amount} 元\n\n"
      f"收據 PDF：\n{pdf_url or '請使用網站上的下載按鈕'}"
  )

  encoded_msg = urllib.parse.quote(line_text)
  line_url = f"https://line.me/R/oaMessage/@813bpsag/?{encoded_msg}"

  st.markdown("---")
  st.link_button("📱 點此打開 LINE 自動發送報名訊息", line_url)