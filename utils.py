import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 🔗 ลิงก์ฐานข้อมูลสเปรดชีตแผ่นงานของคุณ Booska
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/13t_tX5HqXiGucVE-DTt7DgX3xt5ds6nY/gviz/tq?tqx=out:csv&gid=1864070200"

@st.cache_data(ttl=2)
def load_data():
    try:
        # อ่านข้อมูลโดยข้ามแถวที่มีปัญหาด้วย python engine
        df = pd.read_csv(SPREADSHEET_URL, on_bad_lines='skip', engine='python')
        df.columns = df.columns.str.strip()
        
        if df.empty:
            return pd.DataFrame()

        # 🛠️ แผนสำรองอัจฉริยะ: ถ้าหาคอลัมน์ชื่อเฉพาะไม่เจอ ให้จับคู่ตามตำแหน่งคอลัมน์ที่ควรจะเป็นแทนเลย
        has_topic = False
        for col in df.columns:
            if 'Topic' in col or 'risk' in col or 'ประเด็น' in col or 'ความเสี่ยง' in col:
                df = df.rename(columns={col: 'Topic/risk finding'})
                has_topic = True
                break
        
        # ถ้าพยายามหาแล้วยังไม่เจอคำใกล้เคียง บังคับเอาคอลัมน์ที่ 2 (ดัชนี 1) เป็นชื่อหัวข้อแทน
        if not has_topic and len(df.columns) > 1:
            df = df.rename(columns={df.columns[1]: 'Topic/risk finding'})
            
        # เคลียร์ล้างแถวที่ไม่มีชื่อหัวข้อเรื่องความเสี่ยงออก
        if 'Topic/risk finding' in df.columns:
            df = df.dropna(subset=['Topic/risk finding'])
            df = df[df['Topic/risk finding'].astype(str).str.strip() != ""]
        else:
            return pd.DataFrame()

        # กำหนดชื่อคอลัมน์อื่นๆ ตามตำแหน่งเพื่อป้องกันปัญหาพิมพ์ชื่อหัวตารางผิด
        if len(df.columns) > 0:
            date_col = df.columns[0]
            if date_col != 'ว/ด/ป':
                df = df.rename(columns={date_col: 'ว/ด/ป'})

        # กำหนดคอลัมน์ ผู้รับผิดชอบ และ สถานะ ด้วยคำใกล้เคียง
        for col in df.columns:
            if 'Responsible' in col or 'ผู้รับผิดชอบ' in col or 'คนตรวจ' in col:
                if col != 'Responsible Person':
                    df = df.rename(columns={col: 'Responsible Person'})
            if 'Status' in col or 'สถานะ' in col:
                if col != 'Status':
                    df = df.rename(columns={col: 'Status'})

        # ตัดช่องว่างข้อความ
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # ระบบแกะวันที่จากคอลัมน์แรก
        def parse_hospital_date(row):
            try:
                date_val = str(row.get('ว/ด/ป', '')).strip()
                if not date_val or date_val.lower() == 'nan' or date_val == "":
                    return None
                
                if '/' in date_val:
                    parts = date_val.split('/')
                    p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
                    
                    if p3 > 2500:
                        p3 = p3 - 543
                    elif p3 < 100:
                        p3 = p3 + 2000
                        
                    if p1 > 12:
                        return pd.Timestamp(year=p3, month=p2, day=p1).date()
                    else:
                        try:
                            return pd.Timestamp(year=p3, month=p1, day=p2).date()
                        except:
                            return pd.Timestamp(year=p3, month=p2, day=p1).date()
                
                return pd.to_datetime(date_val).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        
        # เคลียร์สูตรล้างรูปภาพ
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
