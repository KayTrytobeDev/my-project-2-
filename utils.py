import streamlit as st
import pandas as pd

# ลิงก์เชื่อมโยงกับ Google Sheet หลักของคุณ
SHEET_ID = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"

@st.cache_data(ttl=5)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()  # ตัดช่องว่างที่หัวคอลัมน์ออกทั้งหมด
        
        # 💡 จับคู่ชื่อหัวคอลัมน์อัจฉริยะ (Keyword Mapping) เผื่อมีการแก้ไขชื่อในสเปรดชีต
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
        
        # ป้องกันตารางพัง: สร้างคอลัมน์เปล่าสำรองไว้หากใน Google Sheet ลืมสร้างไว้
        standard_cols = ['ว/ด/ป', 'Picture (before)', 'Picture (After)', 'Responsible Person', 'Status', 'Topic/risk finding', 'Location', 'Corrective Action']
        for col in standard_cols:
            if col not in df.columns:
                df[col] = None

        # แปลงวันที่แบบปลอดภัย (ช่องไหนไม่ใช่วันที่จะกลายเป็น NaT แทนการเกิด Error)
        df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"ไม่สามารถโหลดข้อมูลจากสเปรดชีตได้: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    """ฟังก์ชันคัดกรองสถานะออกเป็น 3 คลาสหลัก สำหรับกำหนดสีการแสดงผล"""
    if pd.isna(status_value):
        return "pending"
        
    status_str = str(status_value).strip().lower()
    
    # 1. กลุ่มเสร็จสิ้น (Complete) -> สีเขียว
    if any(x in status_str for x in ["เรียบร้อย", "complete", "เสร็จสิ้น", "สำเร็จ", "✅", "done"]):
        return "complete"
    # 2. กลุ่มกำลังทำ (On process) -> สีฟ้า
    elif any(x in status_str for x in ["on process", "onprocess", "กำลังทำ", "ดำเนิน", "🔄"]):
        return "on_process"
    # 3. กลุ่มค้างคา (Pending) -> สีส้ม
    else:
        return "pending"
