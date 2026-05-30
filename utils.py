import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ดาวน์โหลดฐานข้อมูลคัดลอกจากสเปรดชีตแผ่นงาน "สรุปรวม (2)" ของคุณ
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/13t_tX5HqXiGucVE-DTt7DgX3xt5ds6nY/gviz/tq?tqx=out:csv&gid=1864070200"

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(SPREADSHEET_URL, on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        
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

        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        def parse_hospital_date(row):
            try:
                date_col = 'ว/ด/ป' if 'ว/ด/ป' in df.columns else ('Date' if 'Date' in df.columns else df.columns[1])
                date_val = str(row.get(date_col, '')).strip()
                if not date_val or date_val.lower() == 'nan' or date_val == "":
                    return None
                if '/' in date_val:
                    parts = date_val.split('/')
                    year_val = int(parts[2])
                    if year_val > 2500:
                        year_val = year_val - 543
                    if int(parts[0]) > 12:
                        return pd.Timestamp(year=year_val, month=int(parts[1]), day=int(parts[0])).date()
                    else:
                        return pd.Timestamp(year=year_val, month=int(parts[0]), day=int(parts[1])).date()
                return None
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        
        def clean_image_formula(val):
            val_str = str(val).strip()
            if val_str.startswith('=IMAGE("') and val_str.endswith('")'):
                return val_str[8:-2]
            return val_str
            
        if 'Picture (before)' in df.columns:
            df['Picture (before)'] = df['Picture (before)'].apply(clean_image_formula)
        if 'Picture (After)' in df.columns:
            df['Picture (After)'] = df['Picture (After)'].apply(clean_image_formula)

        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"ระบบไม่สามารถดึงข้อมูลได้: {e}")
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
        image.thumbnail((400, 400))
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=60)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except:
        return ""
