import streamlit as st
import requests

# 讀取 Secrets 設定
GAS_WEB_APP_URL = st.secrets["GAS_WEB_APP_URL"]
GAS_API_KEY = st.secrets["GAS_API_KEY"]
SHEET_INCOME_ID = st.secrets["SHEET_INCOME_ID"]
SHEET_CATEGORY_ID = st.secrets["SHEET_CATEGORY_ID"]
SHEET_2026_JIGAI_ID = st.secrets["SHEET_2026_JIGAI_ID"]
LINE_CHANNEL_ACCESS_TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = st.secrets["LINE_USER_ID"]

def call_gas(action, payload):
    payload["action"] = action
    payload["apiKey"] = GAS_API_KEY
    response = requests.post(GAS_WEB_APP_URL, json=payload)
    return response.json()

st.title("⛩️ 法會點選報名系統")

# 初始化 Session State
if "matched_addresses" not in st.session_state:
    st.session_state.matched_addresses = []
if "selected_address" not in st.session_state:
    st.session_state.selected_address = None
if "people_list" not in st.session_state:
    st.session_state.people_list = []
if "search_done" not in st.session_state:
    st.session_state.search_done = False

# 步驟一：輸入姓名查詢
input_name = st.text_input("請輸入姓名查詢地址：")

if st.button("查詢地址"):
    if input_name.strip():
        res = call_gas("search_jigai_2026", {
            "sheetId": SHEET_2026_JIGAI_ID,
            "name": input_name.strip()
        })
        
        if res.get("status") == "success":
            addresses = res.get("addresses", [])
            st.session_state.matched_addresses = addresses
            st.session_state.search_done = True
            st.session_state.selected_address = None
            st.session_state.people_list = []
            
            if not addresses:
                st.warning("去年未參與祭改，請直接回原報名連結進行填寫")
        else:
            st.error("查詢失敗，請檢查 API 設定。")

# 步驟二：選擇地址並帶出同住址所有人員
if st.session_state.search_done and st.session_state.matched_addresses:
    st.success(f"找到 {len(st.session_state.matched_addresses)} 個相關地址，請點擊確認地址：")
    
    for idx, addr in enumerate(st.session_state.matched_addresses):
        if st.button(f"確認地址：{addr}", key=f"addr_btn_{idx}"):
            st.session_state.selected_address = addr
            # 查詢該地址下所有人
            people_res = call_gas("search_jigai_2026", {
                "sheetId": SHEET_2026_JIGAI_ID,
                "address": addr
            })
            if people_res.get("status") == "success":
                st.session_state.people_list = [p["name"] for p in people_res.get("people", [])]

# 步驟三：顯示名單與勾選 116年(2027年) 祭改
if st.session_state.selected_address and st.session_state.people_list:
    st.markdown("---")
    st.write(f"**確認地址：** {st.session_state.selected_address}")
    st.write(f"**相同住址成員（共 {len(st.session_state.people_list)} 人）：** {', '.join(st.session_state.people_list)}")

    jigai_checkbox = st.checkbox("參加 116年(2027年) 祭改")

    if jigai_checkbox:
        count = len(st.session_state.people_list)
        # 單價設定（預設 300/人，可從科目金額表獲取）
        unit_price = 300
        total_amount = count * unit_price
        
        summary_text = f"116年(2027年)祭改人數 {count} 人，金額為 {total_amount} 元"
        st.info(summary_text)

        confirm_amount = st.checkbox("點擊確認金額無誤")

        if confirm_amount:
            if st.button("確認送出報名"):
                with st.spinner("資料處理中，發送至官方 LINE 與收入表..."):
                    submit_res = call_gas("submit_registration", {
                        "incomeSheetId": SHEET_INCOME_ID,
                        "address": st.session_state.selected_address,
                        "peopleNames": st.session_state.people_list,
                        "count": count,
                        "totalAmount": total_amount,
                        "lineToken": LINE_CHANNEL_ACCESS_TOKEN,
                        "lineUserId": LINE_USER_ID
                    })

                    if submit_res.get("status") == "success":
                        st.success("🎉 報名成功！已同步發送至官方 Line 及收入表。")
                        st.write(f"**收據編號：** `{submit_res.get('receiptNo')}`")
                        st.write(f"**訊息備註：** {submit_res.get('message')}")
                        st.image(submit_res.get("qrCodeUrl"), caption="繳款 QR Code 連結", width=200)
                        st.warning("⚠️ 繳款時請提供收據編號或 QR code 連結。")
                    else:
                        st.error("報名失敗，請稍後再試。")