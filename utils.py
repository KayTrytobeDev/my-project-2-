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
        
        # ค้นหาและกำหนดคอลัมน์ประเด็นความเสี่ยง
        if 'Topic/risk finding' not do_any:
            for col in df.columns:
                if 'Topic/risk finding' in col or 'ประเด็นความเสี่ยง' in col:
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

        # ฟังก์ชันแกะอ่านค่า วันเดือนปี จากคอลัมน์เดียวของโรงพยาบาล (เช่น 5/19/2569 หรือ 5/19/2026)
        def parse_hospital_date(row):
            try:
                # ปรับให้ค้นหาชื่อคอลัมน์แรกๆ ที่มักเป็นคอลัมน์ วันที่/ว/ด/ป
                date_col = 'ว/ด/ป' if 'ว/ด/ป' in df.columns else ('Date' if 'Date' in df.columns else df.columns[1])
                date_val = str(row.get(date_col, '')).strip()
                
                if not date_val or date_val.lower() == 'nan':
                    return None
                
                # รองรับฟอร์แมตผสมที่มีเครื่องหมายทับ เช่น 5/19/2569 หรือ 19/5/2026
                if '/' in date_val:
                    parts = date_val.split('/')
                    # กรณีเป็นปี พ.ศ. ให้ทอนกลับเป็น ค.ศ. สำหรับใช้ในระบบ Python Calendar (2569 - 543 = 2026)
                    year_val = int(parts[2])
                    if year_val > 2500:
                        year_val = year_val - 543
                    
                    # ตรวจสอบรูปแบบเดือนขึ้นก่อน หรือวันขึ้นก่อน
                    if int(parts[0]) > 12: # รูปแบบ วัน/เดือน/ปี
                        return pd.Timestamp(year=year_val, month=int(parts[1]), day=int(parts[0])).date()
                    else: # รูปแบบ เดือน/วัน/ปีตามโครงสร้างชีทโรงพยาบาลเดิม
                        return pd.Timestamp(year=year_val, month=int(parts[0]), day=int(parts[1])).date()
                
                # ตลบหลังกรณีข้อมูลไหลหลุดไปอยู่ในรูปแบบคอลัมน์แยก (Date + Month) แบบแถวเก่า
                day_val = str(row.get('Date', '')).strip()
                month_val = str(row.get('Month', '')).strip()
                if day_val and month_val and day_val.lower() != 'nan' and month_val.lower() != 'nan':
                    if '.' in day_val: day_val = day_val.split('.')[0]
                    months_map = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
                    m_num = months_map.get(month_val.lower()[:3], 1)
                    return pd.Timestamp(year=2026, month=m_num, day=int(day_val)).date()
                return None
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        
        # คลีนฟังก์ชันสกัดเอา URL แท้ๆ ออกมาจากสูตร =IMAGE("url") เพื่อให้ Streamlit เอาไปแสดงผลพรีวิวได้ถูกต้อง
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
        # ปรับขยายขนาดพรีวิวสูงสุดให้อยู่ในเกณฑ์เหมาะสมสำหรับจัดเก็บลงเซลล์ Sheet
        image.thumbnail((400, 400))
        buffered = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=60)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except:
        return ""
