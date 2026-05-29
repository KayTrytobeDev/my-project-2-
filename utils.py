import streamlit as st
import pandas as pd

@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    df = pd.read_csv(url)
    # ล้างช่องว่างทั้งชื่อคอลัมน์และข้อมูลด้านใน
    df.columns = df.columns.str.strip()
    
    # 💡 อุดรอยรั่ว: ถ้าในชีทตั้งชื่อว่า "สถานะ" ให้เปลี่ยนเป็น "Status" อัตโนมัติในระบบ
    if 'สถานะ' in df.columns:
        df = df.rename(columns={'สถานะ': 'Status'})
    if 'ผู้รับผิดชอบ' in df.columns:
        df = df.rename(columns={'ผู้รับผิดชอบ': 'Responsible Person'})
        
    return df

def check_complete(status_text):
    if pd.isna(status_text):
        return False
    status_str = str(status_text).strip()
    return any(word in status_str for word in ["เรียบร้อย", "Complete", "complete", "เสร็จสิ้น"])
