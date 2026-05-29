import streamlit as st
import pandas as pd

@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    # ดักจับชื่อคอลัมน์ภาษาไทย
    if 'สถานะ' in df.columns:
        df = df.rename(columns={'สถานะ': 'Status'})
    if 'ผู้รับผิดชอบ' in df.columns:
        df = df.rename(columns={'ผู้รับผิดชอบ': 'Responsible Person'})
        
    # 💡 แปลงคอลัมน์ ว/ด/ป ให้เป็นข้อมูลวันที่ของ Python (Datetime) เพื่อให้เทียบกับปฏิทินได้แม่นยำ
    if 'ว/ด/ป' in df.columns:
        # พยายามแปลงวันที่แบบยืดหยุ่น (รองรับทั้งรูปแบบ Day/Month/Year และ Year-Month-Day)
        df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
        
    return df

def check_complete(status_text):
    if pd.isna(status_text):
        return False
    status_str = str(status_text).strip()
    return any(word in status_str for word in ["เรียบร้อย", "Complete", "complete", "เสร็จสิ้น"])
