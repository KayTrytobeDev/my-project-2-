import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์สเปรดชีตแผ่นงานของคุณ
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/13t_tX5HqXiGucVE-DTt7DgX3xt5ds6nY/gviz/tq?tqx=out:csv&gid=1864070200"

@st.cache_data(ttl=2)
def load_data():
    try:
        # 🛠️ เพิ่ม on_bad_lines='skip' เพื่อข้ามแถวที่พิมพ์ข้อความยาวเกินไป ไม่ให้ระบบพัง
        df = pd.read_csv(SPREADSHEET_URL, on_bad_lines='skip', engine='python')
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
            # กรองแถวที่ไม่มีข้อมูลประเด็นความเสี่ยงออก
            df = df.dropna(subset=['Topic/risk finding'])
            df = df[df['Topic/risk finding'].astype(str).str.strip() != ""]
        else:
            return pd.DataFrame()

        # เคลียร์ช่องว่าง
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # 🧠 เพิ่มฟังก์ชันการแกะวันที่ขั้นสูง รองรับทั้งพิมพ์ พ.ศ. / ค.ศ. หรือข้อความหลุดมา
        def parse_hospital_date(row):
            try:
                date_col = 'ว/ด/ป' if 'ว/ด/ป' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
                date_val = str(row.get(date_col, '')).strip()
                
                if not date_val or date_val.lower() == 'nan' or date_val == "":
                    return None
                
                # รองรับฟอร์แมตที่มีเครื่องหมาย / เช่น 5/19/2569 หรือ 19/05/2026
                if '/' in date_val:
                    parts = date_val.split('/')
                    p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
                    
                    # ตรวจสอบปี พ.ศ. -> แปลงเป็น ค.ศ.
                    if p3 > 2500:
                        p3 = p3 - 543
                    elif p3 < 100:  # กรณีพิมพ์ปีสั้น เช่น /26
                        p3 = p3 + 2000
                        
                    # ตรวจสอบว่าระบบเขียนแบบ เดือน/วัน/ปี หรือ วัน/เดือน/ปี
                    if p1 > 12:  # แปลว่า p1 เป็น "วัน" ชัวร์ๆ (เช่น 19/5/2569)
                        return pd.Timestamp(year=p3, month=p2, day=p1).date()
                    else:  # กรณีเป็น เดือน/วัน/ปี (เช่น 5/19/2569)
                        try:
                            return pd.Timestamp(year=p3, month=p1, day=p2).date()
                        except:
                            return pd.Timestamp(year=p3, month=p2, day=p1).date()
                
                # ลองแปลงแบบอัตโนมัติถ้าหลุดฟอร์แมตอื่นมา
                return pd.to_datetime(date_val).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        
        # ล้างสูตร IMAGE ออกเพื่อให้ได้ URL รูปภาพแท้ๆ
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
