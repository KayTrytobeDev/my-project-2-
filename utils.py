import streamlit as st
import pandas as pd
import requests
from io import StringIO
import re

# 🔗 ใส่ลิงก์แชร์ปกติที่คุณ Booska ส่งมาได้เลยครับ (ระบบจะแปลงท้ายลิงก์ให้เองอัตโนมัติ)
ORIGINAL_URL = "https://docs.google.com/spreadsheets/d/1O1Titxr4J97TlRP3BV50rfvtRXsvGHTSHu79JvftP_k/edit?usp=sharing"

def get_clean_export_url(url):
    """
    ฟังก์ชันวิเคราะห์และเปลี่ยนรูปประโยคลิงก์ Google Sheet 
    ให้กลายเป็นลิงก์ดึงข้อมูลตารางดิบ (Direct CSV Export) ป้องกันระบบส่งหน้าเว็บ HTML กลับมา
    """
    match = re.search(r"spreadsheets/d/([a-zA-O0-9-_]+)", url)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    return url

@st.cache_data(ttl=1)
def load_data():
    try:
        # แปลงร่างลิงก์ให้ถูกต้องตามโครงสร้างหลังบ้าน
        target_url = get_clean_export_url(ORIGINAL_URL)
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(target_url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        # ตรวจสอบสิทธิ์และโครงสร้างของไฟล์ที่ส่งกลับมา
        if "<html" in response.text.lower() or "google-site-verification" in response.text:
            st.error("⚠️ [ตรวจสอบฝั่ง Google Sheet] ข้อมูลที่ได้ยังคงเป็นหน้าเว็บ HTML โปรดตรวจสอบว่าที่หน้าชีต ได้กดแชร์เป็น 'ทุกคนที่มีลิงก์ (Anyone with the link)' และเลือกสิทธิ์เป็น 'ผู้มีสิทธิ์อ่าน (Viewer)' แล้วจริง ๆ หรือยังนะครับ")
            return pd.DataFrame()

        # อ่านตารางข้อมูล
        df = pd.read_csv(StringIO(response.text), on_bad_lines='skip', engine='python', dtype=str)
        if df.empty:
            return pd.DataFrame()

        # ล้างช่องว่างหัวคอลัมน์
        df.columns = df.columns.str.strip()
        
        # จับคู่คอลัมน์สำคัญให้พุ่งเข้าหาหน้าปฏิทินให้ถูกทิศทาง
        rename_map = {}
        for col in df.columns:
            if any(x in str(col) for x in ['ว/ด/ป', 'Date', 'วันที่']):
                rename_map[col] = 'ว/ด/ป'
            elif any(x in str(col) for x in ['Topic', 'risk', 'ประเด็น', 'ความเสี่ยง']):
                rename_map[col] = 'Topic/risk finding'
            elif any(x in str(col) for x in ['Responsible', 'ผู้รับผิดชอบ', 'คนตรวจ']):
                rename_map[col] = 'Responsible Person'
            elif any(x in str(col) for x in ['Status', 'สถานะ']):
                rename_map[col] = 'Status'
        
        df = df.rename(columns=rename_map)

        # ล้างช่องว่างในทุกเซลล์
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

        # ถอดและแกะรูปแบบวันที่ของระบบโรงพยาบาล
        def parse_date(row):
            date_val = str(row.get('ว/ด/ป', '')).strip()
            if not date_val or any(x in date_val.lower() for x in ['nan', 'null', 'total', 'summary', 'may', 'june', 'สรุป']):
                return None
            try:
                if '/' in date_val:
                    parts = date_val.split('/')
                    if len(parts) == 3:
                        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                        if y > 2500: y -= 543
                        elif y < 100: y += 2000
                        try:
                            return pd.Timestamp(year=y, month=m, day=d).date()
                        except:
                            return pd.Timestamp(year=y, month=d, day=m).date()
                return pd.to_datetime(date_val).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_date, axis=1)
        
        # คัดกรองเอาเฉพาะแถวข้อมูลที่มีเนื้อหาวันที่จริง ๆ เพื่อป้องกันระบบปฏิทินรวน
        df = df.dropna(subset=['Formatted_Date'])
        if 'Topic/risk finding' in df.columns:
            df = df[df['Topic/risk finding'] != ""]

        return df
    except Exception as e:
        st.error(f"❌ ระบบตรวจพบปัญหา: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    status_str = str(status_value).strip().lower()
    if any(x in status_str for x in ["เรียบร้อย", "complete", "เสร็จสิ้น", "สำเร็จ", "✅", "done"]):
        return "complete"
    elif any(x in status_str for x in ["on process", "onprocess", "กำลังทำ", "กำลังดำเนินการ", "🔄"]):
        return "on_process"
    else:
        return "pending"
