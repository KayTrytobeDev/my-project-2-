import streamlit as st
import pandas as pd

# ลิงก์ดึงข้อมูลจาก Google Sheet Master File ของคุณ
SHEET_ID = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"

@st.cache_data(ttl=5)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()  # ล้างช่องว่างหัวคอลัมน์
        
        # 💡 ระบบตรวจจับหัวข้อคำสำคัญอัตโนมัติ (Keyword Mapping)
        mapping = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if 'วัน' in col_lower or 'date' in col_lower or 'ว/ด/ป' in col_lower:
                mapping[col] = 'ว/ด/ป'
            elif 'before' in col_lower or 'ก่อน' in col_lower:
                mapping[col] = 'Picture (before)'
            elif 'after' in col_lower or 'หลัง' in col_lower:
                mapping[col] = 'Picture (After)'
            elif 'responsible' in col_lower or 'ผู้รับผิดชอบ' in col_lower or 'owner' in col_lower:
                mapping[col] = 'Responsible Person'
            elif 'status' in col_lower or 'สถานะ' in col_lower:
                mapping[col] = 'Status'
            elif 'topic' in col_lower or 'ประเด็น' in col_lower or 'finding' in col_lower or 'risk' in col_lower:
                mapping[col] = 'Topic/risk finding'
            elif 'location' in col_lower or 'สถานที่' in col_lower:
                mapping[col] = 'Location'
            elif 'action' in col_lower or 'แก้ไข' in col_lower:
                mapping[col] = 'Corrective Action'

        df = df.rename(columns=mapping)
        
        # สร้างคอลัมน์มาตรฐานสำรองไว้ป้องกันระบบพัง
        for standard_col in ['ว/ด/ป', 'Picture (before)', 'Picture (After)', 'Responsible Person', 'Status', 'Topic/risk finding', 'Location', 'Corrective Action']:
            if standard_col not in df.columns:
                df[standard_col] = None

        # แปลงวันที่ให้อยู่ในรูปแบบที่ระบบเข้าใจได้ปลอดภัย
        df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame()

def get_status_type(status_text):
    """ฟังก์ชันแบ่งกลุ่มสถานะเพื่อนำไปกำหนดสีและแท็ก"""
    if pd.isna(status_text):
        return "pending"
        
    status_str = str(status_text).
