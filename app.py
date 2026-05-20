import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 1. 網頁初始設定 (強制收合，回歸原生按鈕)
# ==========================================
st.set_page_config(
    page_title="新店高中營隊資訊檢索系統", 
    page_icon="🏕️", 
    layout="wide",
    initial_sidebar_state="collapsed" 
)

# ==========================================
# 2. 資料庫連線 (Google Sheets 金鑰設定)
# ==========================================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
gc = gspread.authorize(creds)

sh = gc.open("114營隊推播系統資料庫") 
worksheet = sh.worksheet("營隊資訊")
data = worksheet.get_all_values()

df = pd.DataFrame(data[1:], columns=data[0])


# ==========================================
# 3. 網頁前台設計：學生檢索介面
# ==========================================
# ==========================================
# 3. 網頁前台設計：學生檢索介面
# ==========================================
# ✨ 完美版 CSS：精準隱藏貓咪、保留按鈕、加入科技發光特效
st.markdown(
    """
    <style>
    /* 🎯 精準狙擊：只隱藏右上角的 Deploy (貓咪) 按鈕，絕對不傷及無辜 */
    [data-testid="stDeployButton"] { display: none !important; }
    
    /* 🎯 精準狙擊：隱藏右上角三個點的設定選單 (讓學生無法看見後台選項) */
    [data-testid="MainMenu"] { display: none !important; }
    [data-testid="stToolbarActions"] { display: none !important; }

    /* 🛡️ 隱藏網頁底部的 Made with Streamlit 浮水印 */
    footer { visibility: hidden !important; }

    /* 🚀 科技感標題特效：漸層與霓虹發光 */
    .tech-title {
        background: -webkit-linear-gradient(45deg, #00D2FF, #3A7BD5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0px 0px 20px rgba(0, 210, 255, 0.4);
        margin-bottom: 0px; 
        padding-bottom: 0px;
        font-weight: 900;
        letter-spacing: 2px;
    }
    </style>
    
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 class='tech-title'>新店高中</h1>
        <h1 class='tech-title' style='margin-top: 5px; padding-top: 0px;'>營隊資訊系統</h1>
        <p style='color: #8892B0; margin-bottom: 0px; padding-bottom: 0px; margin-top: 15px;'>您可以直接輸入關鍵字搜尋，</p>
        <p style='color: #8892B0; margin-top: 5px; padding-top: 0px;'>或利用下方選單快速帶入學群</p>
        <p style='color: #8892B0; margin-top: 5px; padding-top: 0px;'>打開左方隱藏欄位留下信箱可以追蹤有興趣的學群資訊喔！</p>
    </div>
    """,
    unsafe_allow_html=True
)
# ⚠️ 提前宣告 groups 變數，防止資料庫為空時引發 NameError
groups = []

if df.empty:
    st.warning("目前還沒有任何營隊資訊喔！請管理員先至試算表新增資料。")
else:
    st.divider() 
    
    # --- 整理學群清單 ---
    all_groups = []
    for g in df['對應學群'].dropna():
        split_groups = [x.strip() for x in str(g).replace("，", ",").split(',') if x.strip()]
        all_groups.extend(split_groups)
    groups = sorted(list(set(all_groups)))
    
    # --- 建立「下拉選單」與「搜尋框」的連動魔法 ---
    def fill_search_bar():
        selected = st.session_state.dropdown_selector
        if selected != "✏️ (自行輸入關鍵字)":
            st.session_state.search_bar = selected
        else:
            st.session_state.search_bar = "" 

    search_query = st.text_input(
        "🔍 搜尋關鍵字、學群或主辦單位：", 
        key="search_bar"
    )

    st.selectbox(
        "💡 快速帶入學群參考：", 
        ["✏️ (自行輸入關鍵字)"] + groups, 
        key="dropdown_selector",
        on_change=fill_search_bar
    )

    st.divider() 

    # --- 資料過濾邏輯 ---
    filtered_df = df.copy()
    
    if search_query:
        mask = (
            filtered_df['對應學群'].astype(str).str.contains(search_query, na=False) |
            filtered_df['營隊名稱'].astype(str).str.contains(search_query, na=False) |
            filtered_df['單位'].astype(str).str.contains(search_query, na=False) |
            filtered_df['關鍵字'].astype(str).str.contains(search_query, na=False)
        )
        filtered_df = filtered_df[mask]

    st.write(f"📊 共找到 **{len(filtered_df)}** 筆符合條件的營隊：")
    
    display_df = filtered_df.drop(columns=['推播狀態'], errors='ignore')
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "營隊連結": st.column_config.LinkColumn(
                "營隊連結",
                display_text="🔗 點擊前往" 
            )
        }
    )

# ==========================================
# 4. 學生訂閱追蹤功能 (支援複選與更新)
# ==========================================
st.sidebar.divider() 
st.sidebar.subheader("📬 訂閱/修改營隊通知")
st.sidebar.markdown("請留下信箱。若先前已訂閱過，再次送出即可直接修改追蹤學群喔！")

sidebar_groups = ["全選"] + groups

with st.sidebar.form("subscription_form"):
    student_name = st.text_input("你的姓名或暱稱：")
    student_email = st.text_input("你的學校 Email：")
    
    track_group = st.multiselect(
        "想追蹤的學群 (可複選)：", 
        options=sidebar_groups,
        default=["全選"]
    )
    
    submit_button = st.form_submit_button("送出訂閱 / 更新")
    
    if submit_button:
        if student_name and student_email and len(track_group) > 0:
            try:
                sub_worksheet = sh.worksheet("學生訂閱")
                track_group_str = ", ".join(track_group)
                existing_emails = sub_worksheet.col_values(2)
                
                if student_email in existing_emails:
                    row_index = existing_emails.index(student_email) + 1
                    sub_worksheet.update_cell(row_index, 1, student_name)
                    sub_worksheet.update_cell(row_index, 3, track_group_str)
                    st.sidebar.success(f"🔄 更新成功！已將您的追蹤名單修改為：\n【{track_group_str}】")
                else:
                    sub_worksheet.append_row([student_name, student_email, track_group_str])
                    st.sidebar.success(f"🎉 訂閱成功！未來有這類營隊會通知你喔！")
                    
            except Exception as e:
                st.sidebar.error("寫入資料庫失敗，請稍後再試。")
        else:
            st.sidebar.warning("請完整填寫姓名、信箱，並至少選擇一個學群喔！")
