import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 วางลิงก์ที่ได้จาก "Publish to web" (ที่เลือกเป็น สรุปรวม (2) และรูปแบบ .csv) ตรงนี้ได้เลยครับ
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgTjP2perBAg1RodNvk1AahEh_OFdhCMzIYxyhQu-yM_Twbg3sbheMyTCWHi1zaw/pubhtml?gid=2134980035&single=true"

@st.cache_data(ttl=5)
def load_data():
    try:
        # อ่านข้อมูลโดยตรงจากลิงก์ CSV ที่ประกาศใช้บนเว็บ
        df = pd.read_csv(SPREADSHEET_URL)
        df.columns = df.columns.str.strip()
        
        # ค้นหาคอลัมน์ประเด็นความเสี่ยง
        target_col = None
        for col in df.columns:
            if 'Topic/risk finding' in col or 'ประเด็นความเสี่ยง' in col:
                target_col = col
                if col != 'Topic/risk finding':
                    df = df.rename(columns={col: 'Topic/risk finding'})
                break
                
        if 'Topic/risk finding' in df.columns:
            df = df.dropna(subset=['Topic/risk finding'])
            df = df[df['Topic/risk finding'].astype(str).str.strip() != ""]
        else:
            return pd.DataFrame()

        # คลีนช่องว่างรอบตัวอักษรของทุกคอลัมน์
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # ฟังก์ชันแปลงคอลัมน์ Date และ Month ให้เป็น Date Object สำหรับปฏิทิน
        def parse_hospital_date(row):
            try:
                day_val = str(row.get('Date', '')).strip()
                month_val = str(row.get('Month', '')).strip()
                
                if not day_val or day_val.lower() == 'nan' or not month_val or month_val.lower() == 'nan':
                    return None
                
                # ล้างจุดทศนิยมกรณีเลขวันติดมาเป็น float (เช่น 13.0 -> 13)
                if '.' in day_val:
                    day_val = day_val.split('.')[0]
                
                # แปลงชื่อเดือนภาษาอังกฤษย่อเป็นตัวเลขเดือน
                months_map = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                m_num = months_map.get(month_val.lower()[:3], 1)
                
                # กำหนดปี พ.ศ. 2569 (ค.ศ. 2026) ตามตารางโครงการ
                return pd.Timestamp(year=2026, month=m_num, day=int(day_val)).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"การเชื่อมต่อดึงข้อมูลผ่าน Publish to Web ขัดข้อง: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    if not status_value or str(status_value).strip() == "":
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
    except:
        return ""
