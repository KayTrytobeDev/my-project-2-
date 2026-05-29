import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ ID ของ Google Sheet หลัก
SHEET_ID = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"

@st.cache_data(ttl=3)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=['Topic/risk finding', 'Responsible Person'], how='all')
        
        # คลีนช่องว่างภายในข้อความเพื่อความปลอดภัย
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # 🛠️ ซ่อมสร้างคอลัมน์แปลงวันทีสำหรับปฏิทิน (เนื่องจากในสเปรดชีตจริงของคุณคอลัมน์ Date มีค่าเป็นตัวเลขโดด ๆ เช่น 19)
        # ระบบจะพยายามเดาวันที่ของปีปัจจุบันให้อัตโนมัติ เพื่อให้แสดงผลบนปฏิทินได้ไม่พัง
        def parse_custom_date(row):
            try:
                d = int(float(str(row.get('Date', '1'))))
                m_str = str(row.get('Month', 'May')).strip().title()[:3]
                months = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
                m = months.get(m_str, 5)
                return pd.Timestamp(year=2026, month=m, day=d).date()
            except:
                return pd.Timestamp.now().date()

        df['Formatted_Date'] = df.apply(parse_custom_date, axis=1)
        return df
    except Exception as e:
        st.error(f"ระบบหลังบ้านไม่สามารถดึงข้อมูลสเปรดชีตได้: {e}")
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
        image.thumbnail((500, 500)) # ควบคุมขนาดให้ประหยัดพื้นที่สเปรดชีต
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=65)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"การแปลงรูปภาพขัดข้อง: {e}")
        return ""
