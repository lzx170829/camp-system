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
st.set_page_config(page_title="營隊資訊檢索系統", page_icon="🏕️", layout="wide")
st.markdown("<h1 style='text-align: center;'>🏕️ 114 營隊資訊檢索系統</h1>", unsafe_allow_html=True)
st.markdown("你可以透過左側面板選擇學群，或在下方直接搜尋你有興趣的關鍵字或單位！")

# 如果資料庫是空的 (只有標題沒有資料)
if df.empty:
    st.warning("目前還沒有任何營隊資訊喔！請管理員先至試算表新增資料。")
else:
    # --- 建立篩選器 (側邊欄與搜尋框) ---
    st.sidebar.header("🔍 營隊篩選器")
    
    # 1. 學群篩選 (自動抓取資料庫裡有出現的學群，並加上"顯示全部"選項)
    groups = ["顯示全部"] + list(df['對應學群'].unique())
    selected_group = st.sidebar.selectbox("請選擇對應學群：", groups)
    
    # 2. 關鍵字搜尋 (主畫面)
    search_query = st.text_input("輸入關鍵字 (例如：醫學、成大、志工)：", "")

    # --- 資料過濾邏輯 ---
    # 複製一份原始資料來過濾
    filtered_df = df.copy()
    
    # 執行學群過濾
    if selected_group != "顯示全部":
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
# 3. 學生訂閱追蹤功能 (移至側邊欄)
# ==========================================
st.sidebar.divider() # 在側邊欄畫一條分隔線
st.sidebar.subheader("📬 訂閱新營隊通知")
st.sidebar.markdown("想第一時間收到通知？請留下信箱！")

# 使用 st.sidebar.form 建立側邊欄表單
with st.sidebar.form("subscription_form"):
    student_name = st.text_input("你的姓名或暱稱：")
    student_email = st.text_input("你的學校 Email：")
    
    # 這裡的 groups 變數會抓取前面已經抓好的學群清單，我們排除第一個"顯示全部"
    track_group = st.selectbox("想追蹤的學群：", groups[1:]) 
    
    # 送出按鈕
    submit_button = st.form_submit_button("送出訂閱")
    
    if submit_button:
        # 檢查是不是每個欄位都有填
        if student_name and student_email and track_group:
            try:
                # 連線到「學生訂閱」分頁
                sub_worksheet = sh.worksheet("學生訂閱")
                # 將學生的資料新增到試算表的最下方新的一行
                sub_worksheet.append_row([student_name, student_email, track_group])
                # 成功訊息也會顯示在側邊欄裡
                st.success(f"🎉 訂閱成功！未來如果有【{track_group}】的新營隊，系統會自動通知你喔！")
            except Exception as e:
                st.error("寫入資料庫失敗，請確認資訊是否有誤。")
        else:
            st.warning("請完整填寫姓名、信箱與想追蹤的學群喔！")
