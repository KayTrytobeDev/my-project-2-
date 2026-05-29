import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# ID ของ Google Sheet หลักของคุณ
SHEET_ID = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"

@st.cache_data(ttl=3)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # กรองแถวว่างเปล่าออก
        df = df.dropna(subset=['Topic/risk finding', 'Responsible Person'], how='all')
        
        # คลีนช่องว่างรอบตัวอักษรของทุกคอลัมน์
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # ระบบสกัดและแปลงวันที่แบบเสถียรสูงสุด (รองรับข้อมูลครบทุกเดือนในสเปรดชีต)
        def parse_custom_date(row):
            try:
                d_raw = str(row.get('Date', '')).strip()
                if '/' in d_raw or '-' in d_raw:
                    return pd.to_datetime(d_raw, errors='coerce').date()
                
                # แปลงค่ากรณีเป็นตัวเลขวันโดดๆ ประกอบกับชื่อเดือน
                if d_raw.replace('.','',1).isdigit():
                    d = int(float(d_raw))
                    m_val = str(row.get('Month', 'Jan')).strip().lower()
                    
                    months_map = {
                        'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 
                        'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12,
                        '1':1, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, '11':11, '12':12
                    }
                    
                    m = 1  # หากหาไม่เจอ ให้ default ไปที่เดือน มกราคม (Jan) เพื่อให้ข้อมูลแสดงผลขึ้นมาก่อน
                    for key, val in months_map.items():
                        if key in m_val:
                            m = val
                            break
                            
                    return pd.Timestamp(year=2026, month=m, day=d).date()
                return None
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_custom_date, axis=1)
        return df
    except Exception as e:
        st.error(f"ระบบหลังบ้านไม่สามารถดึงข้อมูลสเปรดชีตได้: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    if pd.isna(status_value):
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
