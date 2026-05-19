import streamlit as st
import gspread
import pandas as pd

# ==========================================
# 1. 系統後台設定：連線 Google 試算表
# ==========================================
# 讀取 JSON 金鑰檔案 (請確保檔名正確，且放在同一資料夾)
try:
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    # 透過試算表名稱打開檔案
    sh = gc.open("114營隊推播系統資料庫")
    # 選擇「營隊資訊」分頁
    worksheet = sh.worksheet("營隊資訊")
    
    # 將資料抓下來，並轉換成好處理的 Pandas 表格 (DataFrame)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error("⚠️ 無法連線到資料庫，請檢查金鑰檔案是否正確，或試算表名稱是否相符。")
    st.stop() # 如果連線失敗，停止執行下面的網頁

# ==========================================
# 2. 網頁前台設計：學生檢索介面
# ==========================================
st.set_page_config(page_title="新店高中營隊資訊系統", page_icon="🏕️", layout="wide")
st.markdown("<h1 style='text-align: center;'>新店高中營隊資訊系統</h1>", unsafe_allow_html=True)
st.markdown("你可以透過左側面板選擇學群，或在下方直接搜尋你有興趣的關鍵字或單位！")

# 如果資料庫是空的 (只有標題沒有資料)
if df.empty:
    st.warning("目前還沒有任何營隊資訊喔！請管理員先至試算表新增資料。")
else:
    # --- 建立篩選器 (側邊欄與搜尋框) ---
    st.sidebar.header("🔍 營隊篩選器")
    
    # 1. 學群篩選 (自動抓取資料庫裡有出現的學群，並加上"顯示全部"選項)
    groups = ["全選"] + list(df['對應學群'].unique())
    selected_group = st.sidebar.selectbox("請選擇對應學群：", groups)
    
    # 2. 關鍵字搜尋 (主畫面)
    search_query = st.text_input("輸入關鍵字 (例如：醫學、成大、志工)：", "")

    # --- 資料過濾邏輯 ---
    # 複製一份原始資料來過濾
    filtered_df = df.copy()
    
    # 執行學群過濾
    if selected_group != "全選":
        filtered_df = filtered_df[filtered_df['對應學群'] == selected_group]
        
    # 執行關鍵字過濾 (同時比對營隊名稱、單位、關鍵字這三個欄位)
    if search_query:
        # 將資料轉成字串並檢查是否包含搜尋詞
        mask = (
            filtered_df['營隊名稱'].astype(str).str.contains(search_query, na=False) |
            filtered_df['單位'].astype(str).str.contains(search_query, na=False) |
            filtered_df['關鍵字'].astype(str).str.contains(search_query, na=False)
        )
        filtered_df = filtered_df[mask]

    # --- 顯示結果 ---
    st.divider()
    st.subheader(f"共找到 {len(filtered_df)} 筆符合條件的營隊：")
    
    # 隱藏不需要讓學生看到的欄位 (例如推播狀態)
    display_df = filtered_df.drop(columns=['推播狀態'], errors='ignore')
    
    # 使用 Streamlit 內建的精美資料表呈現
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True, # 隱藏最左邊的 0,1,2,3 編號
    )
# ==========================================
# 3. 學生訂閱追蹤功能 (支援複選與更新)
# ==========================================
st.sidebar.divider() 
st.sidebar.subheader("📬 訂閱/修改營隊通知")
st.sidebar.markdown("請留下信箱。若先前已訂閱過，再次送出即可直接修改追蹤學群喔！")

with st.sidebar.form("subscription_form"):
    student_name = st.text_input("你的姓名或暱稱：")
    student_email = st.text_input("你的學校 Email：")
    
    # 1. 改變為 multiselect (複選)，並將「顯示全部」設為預設選項
    # options 直接放 groups (裡面已經包含"顯示全部"與所有學群)
    track_group = st.sidebar.multiselect(
        "想追蹤的學群 (可複選)：", 
        options=groups,
        default=["全選"]
    )
    
    submit_button = st.form_submit_button("送出訂閱 / 更新")
    
    if submit_button:
        # 確認姓名、信箱都有填，且至少有選一個學群
        if student_name and student_email and len(track_group) > 0:
            try:
                sub_worksheet = sh.worksheet("學生訂閱")
                
                # 將複選的結果(串列)用逗號連接成純文字，例如："資訊學群, 工程學群"
                track_group_str = ", ".join(track_group)
                
                # 抓取目前試算表 B 欄 (第 2 欄) 所有的 Email
                existing_emails = sub_worksheet.col_values(2)
                
                # 2. 判斷邏輯：更新或是新增
                if student_email in existing_emails:
                    # 如果信箱存在，找出它在第幾列 (list 索引從 0 開始，但試算表列數從 1 開始，故 +1)
                    row_index = existing_emails.index(student_email) + 1
                    
                    # 更新該列的第 1 欄(姓名)與第 3 欄(學群)
                    sub_worksheet.update_cell(row_index, 1, student_name)
                    sub_worksheet.update_cell(row_index, 3, track_group_str)
                    
                    st.sidebar.success(f"🔄 更新成功！已將您的追蹤名單修改為：\n【{track_group_str}】")
                else:
                    # 如果信箱不存在，就在最下方新增一列
                    sub_worksheet.append_row([student_name, student_email, track_group_str])
                    st.sidebar.success(f"🎉 訂閱成功！未來有這類營隊會通知你喔！")
                    
            except Exception as e:
                st.sidebar.error("寫入資料庫失敗，請稍後再試。")
        else:
            st.sidebar.warning("請完整填寫姓名、信箱，並至少選擇一個學群喔！")
