import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ ID ของ Google Sheet หลักของคุณ
SHEET_ID = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"

@st.cache_data(ttl=3)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # ตัดแถวที่เป็นค่าว่างเปล่าออกไปก่อน
        df = df.dropna(subset=['Topic/risk finding', 'Responsible Person'], how='all')
        
        # คลีนช่องว่างรอบๆ ข้อความของทุกคอลัมน์
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # 🛠️ ฟังก์ชันแปลงคอลัมน์ Date และ Month ให้เป็นระบบวันที่ของปฏิทินแบบปลอดภัยขั้นสุด
        def parse_custom_date(row):
            try:
                # ดึงค่าจากคอลัมน์ Date และ Month
                d_val = str(row.get('Date', '1')).strip()
                m_val = str(row.get('Month', 'May')).strip().title()[:3]
                
                # ถ้าเป็นแถวทดสอบ หรือไม่ใช่ตัวเลข ให้ข้ามไป ไม่ให้ระบบพัง
                if 'test' in d_val.lower() or not d_val.replace('.','',1).isdigit():
                    return None
                
                d = int(float(d_val))
                months = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
                m = months.get(m_val, 5)
                
                # แสดงผลบนปฏิทินของปี 2026 ตามฐานข้อมูลหลัก
                return pd.Timestamp(year=2026, month=m, day=d).date()
            except:
                return None # หากแปลงไม่ได้ให้ส่งค่ากลับเป็น None (ระบบปฏิทินจะข้ามเคสนั้นไป ไม่เออเรอร์หน้าแดง)

        df['Formatted_Date'] = df.apply(parse_custom_date, axis=1)
        return df
    except Exception as e:
        st.error(f"ระบบหลังบ้านไม่สามารถดึงข้อมูลสเปรดชีตได้: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    if pd.isna(status_value):
        return "pending"
    status_str = str(status_value).strip().lower()
    if any(x in status_str for x in ["เรียบร้อย", "complete", "เสร็จสิ้น", "สำเร็จ", "✅", "done", "ดำเนินการเรียบร้อย"]):
        return "complete"
    elif any(x in status_str for x in ["on process", "onprocess", "กำลังทำ", "ดำเนิน", "กำลังดำเนินการ", "🔄"]):
        return "on_process"
    else:
        return "pending"

def convert_image_to_base64(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        image = Image.open(uploaded_file)
        image.thumbnail((500, 500)) # บีบอัดขนาดเพื่อความรวดเร็วในการโหลดรูปภาพ
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=65)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"การแปลงรูปภาพขัดข้อง: {e}")
        return ""
