import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 💡 วางลิงก์สเปรดชีตของคุณตัวล่าสุด (ตรงช่องนี้ให้กดประกาศใช้บนเว็บแบบ CSV หรือดึงโดยตรง)
# หมายเหตุ: หากเปิดแชร์ลิงก์ทั่วไป สามารถใช้ฟังก์ชันนี้แปลงปลายลิงก์ดึงค่า CSV ได้อัตโนมัติ
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/13t_tX5HqXiGucVE-DTt7DgX3xt5ds6nY/export?format=csv&gid=1864070200"

@st.cache_data(ttl=5)
def load_data():
    try:
        # อ่านข้อมูลจากตารางหลัก
        df = pd.read_csv(SPREADSHEET_URL)
        df.columns = df.columns.str.strip()
        
        # กรองเอาเฉพาะแถวที่มีการบันทึกประเด็นความเสี่ยงจริง
        if 'Topic/risk finding' in df.columns:
            df = df.dropna(subset=['Topic/risk finding'])
        else:
            # กรณีหัวคอลัมน์ภาษาไทย/อังกฤษ แตกต่างกันให้ปรับรองรับ
            possible_topics = ['Topic/risk finding', 'ประเด็นความเสี่ยงที่พบ', 'ประเด็นความเสี่ยงที่พบ (Topic/risk finding)']
            for col in possible_topics:
                if col in df.columns:
                    df = df.rename(columns={col: 'Topic/risk finding'})
                    break
            df = df.dropna(subset=['Topic/risk finding'])

        # คลีนช่องว่างรอบตัวอักษรของทุกคอลัมน์
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # 🛠️ จัดการแปลงคอลัมน์ วัน/เดือน/ปี ให้กลายเป็นรูปแบบวันที่ที่ระบุบนปฏิทินได้
        def parse_row_date(row):
            try:
                date_val = str(row.get('วัน/เดือน/ปี', row.get('Date/Month/Year', row.get('Date', '')))).strip()
                if not date_val or date_val.lower() == 'nan':
                    return None
                # รองรับฟอร์แมตวันที่หลากหลายรูปแบบที่พิมพ์ในสเปรดชีต
                return pd.to_datetime(date_val, errors='coerce').date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_row_date, axis=1)
        
        # เติมค่าว่างป้องกัน Error ในระบบ
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"ระบบหลังบ้านไม่สามารถดึงข้อมูลจากลิงก์สเปรดชีตได้: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    if pd.isna(status_value) or str(status_value).strip() == "":
        return "pending"
    status_str = str(status_value).strip().lower()
    if any(x in status_str for x in ["เรียบร้อย", "complete", "เสร็จสิ้น", "สำเร็จ", "✅", "done"]):
        return "complete"
    elif any(x in status_str for x in ["on process", "onprocess", "กำลังทำ", "กำลังดำเนินการ", "🔄"]):
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
        img_str = base64.b64encode(buffered.getvalue()).decode
