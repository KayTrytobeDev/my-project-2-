import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# ID ของ Google Sheet หลักของคุณ
SHEET_ID = "13t_tX5HqXiGucVE-DTt7DgX3xt5ds6nY"

@st.cache_data(ttl=3)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # กรองแถวว่างเปล่าออกโดยอิงจากประเด็นความเสี่ยงเป็นหลัก
        df = df.dropna(subset=['Topic/risk finding'])
        
        # คลีนช่องว่างรอบตัวอักษรของทุกคอลัมน์
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # 🛠️ ระบบแปลงวันที่ปรับปรุงใหม่: รองรับคอลัมน์ "ว/ด/ป" สากลช่องเดียว
        def parse_custom_date(row):
            try:
                # ลองดึงข้อมูลจากคอลัมน์ ว/ด/ป
                date_raw = str(row.get('ว/ด/ป', row.get('Date', ''))).strip()
                if not date_raw or date_raw.lower() == 'nan':
                    return None
                
                # แปลงผ่าน pandas datetime รองรับ format ว/ด/ป สากล
                return pd.to_datetime(date_raw, errors='coerce').date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_custom_date, axis=1)
        
        # ป้องกันค่า NaN ในคอลลัมน์อื่นหลุดไปรบกวนหน้าเว็บ
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"ระบบหลังบ้านไม่สามารถดึงข้อมูลสเปรดชีตได้: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    if pd.isna(status_value) or str(status_value).strip() == "":
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
        image.thumbnail((500, 500))
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=65)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"การแปลงรูปภาพขัดข้อง: {e}")
        return ""
