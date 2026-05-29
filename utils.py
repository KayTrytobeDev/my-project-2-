import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ใส่ ID ของ Google Sheet (แกะมาจากลิงก์สเปรดชีตหลักของคุณเรียบร้อยแล้ว)
SHEET_ID = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"

@st.cache_data(ttl=5)
def load_data():
    # เปลี่ยนมาดึงข้อมูลผ่านรูปแบบ CSV เพื่อให้ได้ข้อความรหัส Base64 เต็ม 100% ไม่โดนระบบตัดคำ
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip() # ล้างช่องว่างที่หัวคอลัมน์
        df = df.dropna(how='all')
        
        # 💡 ระบบ Mapping ชื่อคอลัมน์อัตโนมัติ เผื่อในชีทสะกดต่างกัน
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
        
        # สร้างคอลัมน์มาตรฐานสำรองไว้กันระบบพัง
        standard_cols = ['ว/ด/ป', 'Picture (before)', 'Picture (After)', 'Responsible Person', 'Status', 'Topic/risk finding', 'Location', 'Corrective Action']
        for col in standard_cols:
            if col not in df.columns:
                df[col] = None

        df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"ระบบไม่สามารถดึงข้อมูลสเปรดชีตได้: {e}")
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
        # บีบอัดภาพให้อยู่ในขนาดสูงสุดไม่เกิน 700px เพื่อไม่ให้ความยาวข้อความล้นข้อจำกัดของกูเกิ้ลเซลล์
        image.thumbnail((700, 700))
        
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        # เซฟภาพเป็น JPEG คุณภาพ 70% เพื่อประหยัดพื้นที่บนชีทและทำให้ระบบประมวลผลเร็วขึ้น
        image.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลรูปภาพ: {e}")
        return ""
