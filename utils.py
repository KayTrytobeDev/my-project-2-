import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ Google Sheet ในรูปแบบ Web Publication html สำหรับดึงข้อมูลมาแสดงผล
PUB_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vThLIQuGIL1APAMKSwxNsKmSYoSFxFdJiACw6PRJbzOAoq6SddZmp0bS7-IcYSaTMEq3_e9i2UhqfoU/pubhtml"

@st.cache_data(ttl=5)
def load_data():
    try:
        # อ่านตารางจากหน้า HTML (ดึงตารางแรกที่เจอและใช้แถวที่ 1 เป็นหัวคอลัมน์)
        tables = pd.read_html(PUB_URL, header=1)
        if not tables:
            st.error("ไม่พบตารางข้อมูลในลิงก์ Google Sheet ครับ")
            return pd.DataFrame()
            
        df = tables[0]
        df.columns = df.columns.str.strip() # ล้างช่องว่างที่หัวคอลัมน์
        
        # ตัดแถวที่เป็นค่าว่างทั้งหมด และเอาคอลัมน์ Unnamed ที่ระบบสร้างขึ้นเกินมาออกไป
        df = df.dropna(how='all').loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # 💡 ระบบ Mapping ชื่อคอลัมน์อัตโนมัติ เผื่อใน Google Sheet พิมพ์สะกดต่างกัน
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
        
        # อุดช่องโหว่: สร้างคอลัมน์มาตรฐานทิ้งไว้กรณีใน Sheet ไม่มี จะได้ไม่ขึ้น KeyError
        standard_cols = ['ว/ด/ป', 'Picture (before)', 'Picture (After)', 'Responsible Person', 'Status', 'Topic/risk finding', 'Location', 'Corrective Action']
        for col in standard_cols:
            if col not in df.columns:
                df[col] = None

        # แปลงข้อมูลคอลัมน์วันที่ให้เป็น Date Object แบบไม่พัง
        df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"ระบบหลังบ้านไม่สามารถดึงข้อมูลสเปรดชีตได้: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    """แบ่งกลุ่มสถานะออกเป็น 3 คลาสหลักเพื่อจัดกลุ่มและทำสี UI"""
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
    """แปลงไฟล์รูปภาพที่เลือกให้เป็นข้อความ Base64 พร้อมย่อขนาดเพื่อเซฟลง Sheet อย่างปลอดภัย"""
    if uploaded_file is None:
        return ""
    try:
        image = Image.open(uploaded_file)
        # บีบขนาดด้านกว้างยาวสูงสุดไม่เกิน 700px เพื่อให้ไฟล์เบาและโหลดไว
        image.thumbnail((700, 700))
        
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=70) # บีบอัดคุณภาพรูปที่ 70% ชัดกำลังดีและไฟล์ไม่หนัก
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลรูปภาพ: {e}")
        return ""
