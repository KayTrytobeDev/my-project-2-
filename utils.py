import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# ลิงก์สเปรดชีตของคุณจากแผ่นงานหลัก (คัดลอก ID และ GID ของชีทสรุปรวม 2 เรียบร้อย)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/13t_tX5HqXiGucVE-DTt7DgX3xt5ds6nY/export?format=csv&gid=1864070200"

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(SPREADSHEET_URL)
        df.columns = df.columns.str.strip()
        
        # ค้นหาคอลัมน์ประเด็นความเสี่ยง
        target_col = None
        for col in df.columns:
            if 'Topic/risk finding' in col or 'ประเด็นความเสี่ยงที่พบ' in col:
                target_col = col
                if col != 'Topic/risk finding':
                    df = df.rename(columns={col: 'Topic/risk finding'})
                break
                
        if 'Topic/risk finding' in df.columns:
            df = df.dropna(subset=['Topic/risk finding'])
        else:
            return pd.DataFrame()

        # คลีนช่องว่างข้อความ
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # แปลง วัน และ เดือน จากตารางใหม่ให้เป็น Date Object สำหรับใช้บนปฏิทิน
        def parse_hospital_date(row):
            try:
                day_val = str(row.get('Date', '')).strip()
                month_val = str(row.get('Month', '')).strip()
                
                if not day_val or day_val.lower() == 'nan' or not month_val:
                    return None
                
                # ล้างจุดทศนิยมกรณีดึงเลขวันมาเป็น float (เช่น 13.0 -> 13)
                if '.' in day_val:
                    day_val = day_val.split('.')[0]
                
                # แมปปิ้งชื่อเดือนย่อเป็นตัวเลขเดือน
                months_map = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                m_num = months_map.get(month_val.lower()[:3], 1)
                
                # กำหนดปี พ.ศ. 2569 ตามหัวข้อตารางปฏิทินของคุณ (ค.ศ. 2026)
                return pd.Timestamp(year=2026, month=m_num, day=int(day_val)).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"การดึงข้อมูลจากสเปรดชีตขัดข้อง: {e}")
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
