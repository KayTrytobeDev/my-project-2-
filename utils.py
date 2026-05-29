import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ Google Sheet ใหม่ที่คุณส่งมา (เปิดใช้งานในรูปแบบ Web Publication Html)
PUB_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vThLIQuGIL1APAMKSwxNsKmSYoSFxFdJiACw6PRJbzOAoq6SddZmp0bS7-IcYSaTMEq3_e9i2UhqfoU/pubhtml"

@st.cache_data(ttl=5)
def load_data():
    try:
        # อ่านข้อมูลจากหน้าเว็บที่แชร์สาธารณะ (ดึงตารางแรกที่พบในหน้า html)
        tables = pd.read_html(PUB_URL, header=1)
        if not tables:
            st.error("ไม่พบข้อมูลตารางในลิงก์ Google Sheet ที่ระบุ")
            return pd.DataFrame()
            
        df = tables[0]
        
        # คลีนข้อมูลคอลัมน์และช่องว่าง
        df.columns = df.columns.str.strip()
        # ลบแถวหรือคอลัมน์ที่เป็นค่าว่างทั้งหมดที่อาจหลุดมาจากระบบ Html
        df = df.dropna(how='all').loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # 💡 ระบบจับคู่ชื่อหัวคอลัมน์อัจฉริยะ (Keyword Mapping)
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
        
        # ป้องกันตารางพัง: สร้างคอลัมน์เปล่าสำรองไว้ล่วงหน้า
        standard_cols = ['ว/ด/ป', 'Picture (before)', 'Picture (After)', 'Responsible Person', 'Status', 'Topic/risk finding', 'Location', 'Corrective Action']
        for col in standard_cols:
            if col not in df.columns:
                df[col] = None

        # แปลงวันที่แบบปลอดภัย
        df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลจากลิงก์สเปรดชีตสาธารณะได้: {e}")
        st.info("💡 แนะนำให้ตรวจสอบว่าได้ตั้งค่า 'เผยแพร่ไปยังเว็บ (Publish to web)' บน Google Sheet เรียบร้อยแล้วหรือยัง")
        return pd.DataFrame()

def get_status_group(status_value):
    if pd.isna(status_value):
        return "pending"
    status_str = str(status_value).strip().lower()
    if any(x in status_str for x in ["เรียบร้อย", "complete", "เสร็จสิ้น", "สำเร็จ", "✅", "done"]):
        return "complete"
    elif any(x in status_str for x in ["on process", "onprocess", "กำลังทำ", "ดำเนิน", "🔄"]):
        return "on_process"
    else:
        return "pending"

def convert_image_to_base64(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        image = Image.open(uploaded_file)
        image.thumbnail((800, 800))
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=75)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการแปลงไฟล์รูปภาพ: {e}")
        return ""
