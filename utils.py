import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ฐานข้อมูลจากแผ่นงาน "สรุปรวม (2)" ของคุณ Booska
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1CN0i5qlvgAo5w1QG0sHBl1Z4WyB8Hl9VZSK0HnqqU4c/edit?usp=sharing"

@st.cache_data(ttl=2)
def load_data():
    try:
        # ดึงข้อมูลโดยข้ามแถวที่พิมพ์ข้อความยาวเกินไป เพื่อไม่ให้ระบบล่ม (on_bad_lines='skip')
        df = pd.read_csv(SPREADSHEET_URL, on_bad_lines='skip', engine='python')
        df.columns = df.columns.str.strip()
        
        # ล้างช่องว่างของชื่อคอล็มน์และเปลี่ยนชื่อคอลัมน์ประเด็นความเสี่ยงให้เป็นสากล
        for col in df.columns:
            if 'Topic/risk finding' in col or 'ประเด็นความเสี่ยง' in col:
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

        # ฟังก์ชันแกะฟอร์แมตวันที่อัจฉริยะ (รองรับระบบ ว/ด/ป ปีพ.ศ. และ ปีค.ศ.)
        def parse_hospital_date(row):
            try:
                date_col = 'ว/ด/ป' if 'ว/ด/ป' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
                date_val = str(row.get(date_col, '')).strip()
                
                if not date_val or date_val.lower() == 'nan' or date_val == "":
                    return None
                
                if '/' in date_val:
                    parts = date_val.split('/')
                    p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
                    
                    # ถ้าปีเป็น พ.ศ. เกิน 2500 ให้แปลงกลับเป็น ค.ศ. สำหรับระบบปฏิทิน Python
                    if p3 > 2500:
                        p3 = p3 - 543
                    elif p3 < 100:
                        p3 = p3 + 2000
                        
                    # เช็กว่าเขียนแบบ วัน/เดือน/ปี หรือ เดือน/วัน/ปี
                    if p1 > 12:  # ชัวร์ว่าเป็นวันที่แน่นอน เช่น 19/5/2569
                        return pd.Timestamp(year=p3, month=p2, day=p1).date()
                    else:  # กรณีเป็น เดือน/วัน/ปี หรือ วัน/เดือน/ปี ที่ไม่เกินเลข 12
                        try:
                            return pd.Timestamp(year=p3, month=p1, day=p2).date()
                        except:
                            return pd.Timestamp(year=p3, month=p2, day=p1).date()
                
                return pd.to_datetime(date_val).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        
        # แกะ URL รูปภาพออกจากสูตร =IMAGE("...") เพื่อนำมาพรีวิวใน Streamlit
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
        st.error(f"ระบบตรวจพบฟอร์แมตข้อมูลขัดข้องในสเปรดชีต: {e}")
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
