import streamlit as st
import pandas as pd
import requests
import base64
from io import BytesIO, StringIO
from PIL import Image

# 🔗 เชื่อมต่อโดยตรงกับสเปรดชีตอันใหม่ที่คุณ Booska จัดทำขึ้น
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1O1Titxr4J97TlRP3BV50rfvtRXsvGHTSHu79JvftP_k/export?format=csv&gid=0"

@st.cache_data(ttl=1)
def load_data():
    try:
        # ดึงข้อมูลดิบจาก Google Sheets ใหม่
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(SPREADSHEET_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        # กลไกดักจับกรณีลืมเปิดแชร์สิทธิ์การเข้าถึงทั่วไป
        if "<html" in response.text.lower() or "google-site-verification" in response.text:
            st.warning("⚠️ [สิทธิ์การเข้าถึงถูกปิดกั้น] อย่าลืมกดปุ่ม 'แชร์ (Share)' ที่มุมขวาบนของ Google Sheet แผ่นใหม่ แล้วปรับสิทธิ์ให้เป็น 'ทุกคนที่มีลิงก์ (Anyone with the link)' ด้วยนะครับ")
            return pd.DataFrame()

        # แปลงข้อความดิบให้กลายเป็นตาราง DataFrame
        df = pd.read_csv(
            StringIO(response.text),
            on_bad_lines='skip',
            engine='python',
            dtype=str
        )
        
        if df.empty:
            return pd.DataFrame()

        # ล้างช่องว่างที่หัวคอลลัมน์ทั้งหมดเพื่อป้องกัน Key Error
        df.columns = df.columns.str.strip()
        
        # ค้นหาและจับคู่คอลัมน์ประเด็นความเสี่ยงตามโครงสร้างชีตใหม่
        has_topic = False
        for col in df.columns:
            if any(x in str(col) for x in ['Topic', 'risk', 'ประเด็น', 'ความเสี่ยง']):
                df = df.rename(columns={col: 'Topic/risk finding'})
                has_topic = True
                break
        
        if not has_topic and len(df.columns) > 1:
            df = df.rename(columns={df.columns[1]: 'Topic/risk finding'})
            
        # เคลียร์ช่องว่างข้อความส่วนเกินในทุก ๆ เซลล์เพื่อความสะอาดของข้อมูล
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

        # ระบบแกะรอยฟอร์แมตวันที่ (รองรับทั้งระบบปี พ.ศ. และ ค.ศ. บนโครงสร้างใหม่)
        def parse_hospital_date(row):
            try:
                date_val = str(row.get('ว/ด/ป', '')).strip()
                if not date_val or date_val.lower() in ['nan', 'none', 'null', '', 'may', 'june', 'total', 'สรุป']:
                    return None
                
                if '/' in date_val:
                    parts = date_val.split('/')
                    if len(parts) != 3:
                        return None
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

        # ตั้งชื่อคอลัมน์แรกให้เป็นวันที่มาตรฐาน
        if len(df.columns) > 0:
            date_col = df.columns[0]
            if date_col != 'ว/ด/ป':
                df = df.rename(columns={date_col: 'ว/ด/ป'})
                
        df['Formatted_Date'] = df.apply(parse_hospital_date, axis=1)
        
        # ตัดแถวที่ไม่สามารถแปลงเป็นวันที่ออก เพื่อไม่ให้ระบบวาดปฏิทินพัง
        df = df.dropna(subset=['Formatted_Date'])
        
        if 'Topic/risk finding' in df.columns:
            df = df[df['Topic/risk finding'] != ""]

        # ค้นหาและเปลี่ยนชื่อคอลัมน์ผู้รับผิดชอบและสถานะงานให้ตรงกับหน้าแอปหลัก
        for col in df.columns:
            if any(x in str(col) for x in ['Responsible', 'ผู้รับผิดชอบ', 'คนตรวจ']):
                df = df.rename(columns={col: 'Responsible Person'})
            if any(x in str(col) for x in ['Status', 'สถานะ']):
                df = df.rename(columns={col: 'Status'})

        # ฟังก์ชันแกะลิงก์รูปภาพในกรณีที่ทีมงานพิมพ์สูตร =IMAGE()
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
        st.error(f"ระบบตรวจพบข้อผิดพลาดในการประมวลผลสเปรดชีตใหม่: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    if not status_value or str(status_value).strip() == "":
        return "pending"
    status_str = str(status_value).strip().lower()
    if any(x in status_str for x in ["เรียบร้อย", "complete", "เสร็จสิ้น", "สำเร็จ", "✅", "done"]):
        return "complete"
    elif any(x in status_str for x in ["on process", "onprocess", "กำลังทำ", "กำลังดำเนินการ", "🔄"]):
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
        return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    except:
        return ""
