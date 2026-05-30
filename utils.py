import streamlit as st
import pandas as pd
import base64
import requests
from io import BytesIO, StringIO
from PIL import Image

# 🔗 ลิงก์ฐานข้อมูลแบบยืดหยุ่น (บอสใช้ฟอร์แมตดึงตารางดิบโดยตรง)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSUClxj5_aIOhr2GQ_vTd3IGhrR1MKJxjwp_-wAVrafYLbylhME-gfokR8BfbXiSiz_oPQldAu6J-5g/pubhtml?gid=2134980035&single=true"

@st.cache_data(ttl=2)
def load_data():
    try:
        # ดึงข้อความจากลิงก์สเปรดชีต
        response = requests.get(SPREADSHEET_URL, timeout=15)
        response.encoding = 'utf-8'
        
        # 🚨 ถ้าหน้าเว็บถูกปิดกั้น สเปรดชีตจะส่งรหัส HTML กลับมาแทนตารางข้อมูล
        if "<html" in response.text.lower() or "<meta" in response.text.lower() or "google-site-verification" in response.text:
            st.warning("⚠️ [สิทธิ์การเข้าถึงถูกปิดกั้น] โปรดตรวจสอบว่าใน Google Sheet ได้เปลี่ยนการเข้าถึงทั่วไปเป็น 'ทุกคนที่มีลิงก์' แล้วหรือยังครับ")
            return pd.DataFrame()

        # อ่านข้อมูลตารางจากหน้าข้อความดิบ
        df = pd.read_csv(
            StringIO(response.text),
            on_bad_lines='skip',
            engine='python',
            dtype=str
        )
        
        if df.empty:
            return pd.DataFrame()

        # ล้างช่องว่างที่หัวคอลลัมน์ทั้งหมด
        df.columns = df.columns.str.strip()
        
        # ค้นหาคอลลัมน์ประเด็นความเสี่ยง
        has_topic = False
        for col in df.columns:
            if any(x in str(col) for x in ['Topic', 'risk', 'ประเด็น', 'ความเสี่ยง']):
                df = df.rename(columns={col: 'Topic/risk finding'})
                has_topic = True
                break
        
        if not has_topic and len(df.columns) > 1:
            df = df.rename(columns={df.columns[1]: 'Topic/risk finding'})
            
        # คัดกรองเฉพาะแถวที่มีข้อความบันทึกความเสี่ยงจริง
        if 'Topic/risk finding' in df.columns:
            df = df.dropna(subset=['Topic/risk finding'])
            df = df[df['Topic/risk finding'].astype(str).str.strip() != ""]
            df = df[~df['Topic/risk finding'].astype(str).str.contains('nan|None|null|<meta|<html', case=False)]
        else:
            return pd.DataFrame()

        # กำหนดชื่อคอลัมน์แรกให้เป็นวันที่
        if len(df.columns) > 0:
            date_col = df.columns[0]
            if date_col != 'ว/ด/ป':
                df = df.rename(columns={date_col: 'ว/ด/ป'})

        # กำหนดชื่อคอลัมน์ผู้รับผิดชอบและสถานะงาน
        for col in df.columns:
            if any(x in str(col) for x in ['Responsible', 'ผู้รับผิดชอบ', 'คนตรวจ']):
                if col != 'Responsible Person':
                    df = df.rename(columns={col: 'Responsible Person'})
            if any(x in str(col) for x in ['Status', 'สถานะ']):
                if col != 'Status':
                    df = df.rename(columns={col: 'Status'})

        # ล้างช่องว่างรอบตัวอักษรของทุกเซลล์ในตาราง
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

        # แปลงฟอร์แมตวันที่ (พ.ศ. เป็น ค.ศ.)
        def parse_hospital_date(row):
            try:
                date_val = str(row.get('ว/ด/ป', '')).strip()
                if not date_val or date_val.lower() in ['nan', 'none', 'null', '']:
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
        
        # ถอดสูตรแปลงลิงก์รูปภาพ
        def clean_image_formula(val):
            val_str = str(val).strip()
            if val_str.startswith('=IMAGE("') and val_str.endswith('")'):
                return val_str[8:-2]
            return val_str
            
        if 'Picture (before)' in df.columns:
            df['Picture (before)'] = df['Picture (before)'].apply(clean_image_formula)
        if 'Picture (After)' in df.columns:
            df['Picture (After)'] = df['Picture (After)'].apply(clean_image_formula)

        return df
    except Exception as e:
        st.error(f"ระบบขัดข้อง: {e}")
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
