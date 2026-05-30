import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ดาวน์โหลดฐานข้อมูล CSV ที่เจาะจงไปยังแผ่นงาน "สรุปรวม (2)" ของคุณโดยตรง
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgTjP2perBAg1RodNvk1AahEh_OFdhCMzIYxyhQu-yM_Twbg3sbheMyTCWHi1zaw/pubhtml?gid=2134980035&single=true"

@st.cache_data(ttl=5)
def load_data():
    try:
        # ใช้ on_bad_lines='skip' เพื่อข้ามแถวว่างด้านล่างที่มีจำนวนคอลัมน์เพี้ยน (แก้ปัญหา Expected 6 fields, saw 10)
        df = pd.read_csv(SPREADSHEET_URL, on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        
        # ตรวจสอบและตั้งชื่อคอลัมน์หลักให้ตรงกับชีทปัจจุบัน
        possible_topics = ['Topic/risk finding', 'ประเด็นความเสี่ยงที่พบ', 'Topic']
        for col in possible_topics:
            if col in df.columns:
                if col != 'Topic/risk finding':
                    df = df.rename(columns={col: 'Topic/risk finding'})
                break
                
        if 'Topic/risk finding' in df.columns:
            # ลบแถวที่เป็นค่าว่างหรือตัวข้อความหัวตารางส่วนเกินออก
            df = df.dropna(subset=['Topic/risk finding'])
            df = df[df['Topic/risk finding'].astype(str).str.strip() != ""]
        else:
            return pd.DataFrame()

        # ล้างช่องว่างข้อความรอบตัวอักษรของทุกคอลัมน์เพื่อความแม่นยำในการกรอง
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # ฟังก์ชันจัดฟอร์แมตแปลง วัน (Date) และ เดือน (Month) เป็นระบบวันที่สากล
        def parse_hospital_date(row):
            try:
                day_val = str(row.get('Date', '')).strip()
                month_val = str(row.get('Month', '')).strip()
                
                if not day_val or day_val.lower() == 'nan' or not month_val or month_val.lower() == 'nan':
                    return None
                
                # ตัดเศษทศนิยมกรณีดึงเลขวันมาเป็น float (เช่น 13.0 -> 13)
                if '.' in day_val:
                    day_val = day_val.split('.')[0]
                
                # แมปชื่อเดือนย่อเป็นตัวเลขเดือนประจำปี
                months_map = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                m_num = months_map.get(month_val.lower()[:3], 1)
                
                # ล็อกปีตามปฏิทินตรวจ FMS Round พ.ศ. 2569 (ตรงกับ ค.ศ. 2026)
                return pd.Timestamp(year=2026, month=m_num, day=int(day_val)).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"ระบบไม่สามารถดึงข้อมูลจากสเปรดชีตได้เนื่องจากโครงสร้างแถวในชีทมีปัญหา: {e}")
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
