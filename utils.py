import streamlit as st
import pandas as pd

# ลิงก์สำหรับดึงข้อมูลจาก Master File ของคุณ
SHEET_ID = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"

@st.cache_data(ttl=5)  # ดึงข้อมูลใหม่ทุกๆ 5 วินาทีเพื่อความสดใหม่ของข้อมูล
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()  # ลบช่องว่างหัวคอลัมน์ออก
        
        # 💡 ปรับปรุงกลไกจับคำสำคัญ (Keyword Mapping) ให้ตรงกับสเปรดชีตล่าสุดของคุณ
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
            elif 'topic' in col_lower or 'ประเด็น' in col_lower or 'finding' in col_lower or ' risk' in col_lower:
                mapping[col] = 'Topic/risk finding'
            elif 'location' in col_lower or 'สถานที่' in col_lower:
                mapping[col] = 'Location'
            elif 'action' in col_lower or 'แก้ไข' in col_lower:
                mapping[col] = 'Corrective Action'

        df = df.rename(columns=mapping)
        
        # ป้องกันระบบพังเผื่อกรณีบางคอลัมน์พิมพ์ไม่ตรงจริงๆ ให้ใส่คอลัมน์เปล่ารอไว้เลย
        for standard_col in ['ว/ด/ป', 'Picture (before)', 'Picture (After)', 'Responsible Person', 'Status', 'Topic/risk finding', 'Location', 'Corrective Action']:
            if standard_col not in df.columns:
                df[standard_col] = None

        # แปลงเป็นวันที่แบบปลอดภัย (ระบุวันที่ไม่ได้จะกลายเป็น NaT แทนที่จะระเบิดเป็น Error)
        df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อสเปรดชีต: {e}")
        return pd.DataFrame()

def check_complete(status_text):
    if pd.isna(status_text):
        return False
    status_str = str(status_text).strip()
    # ดักจับทุกสถานะความสำเร็จที่เป็นไปได้
    return any(word in status_str for word in ["เรียบร้อย", "Complete", "complete", "เสร็จสิ้น", "สำเร็จ", "✅"])
