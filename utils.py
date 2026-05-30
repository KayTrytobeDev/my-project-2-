import streamlit as st
import pandas as pd
import requests
from io import StringIO

# 🔗 ลิงก์ตรงดึงข้อมูล CSV จาก Google Sheet ใบใหม่ของคุณ Booska
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1O1Titxr4J97TlRP3BV50rfvtRXsvGHTSHu79JvftP_k/export?format=csv&gid=0"

@st.cache_data(ttl=1)
def load_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(SPREADSHEET_URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        # ตรวจสอบสิทธิ์การเข้าถึงสเปรดชีต
        if "<html" in response.text.lower() or "google-site-verification" in response.text:
            st.warning("⚠️ [สิทธิ์ถูกปิดกั้น] โปรดกดปุ่ม 'แชร์ (Share)' ขวาบนใน Google Sheet แล้วเปลี่ยนเป็น 'ทุกคนที่มีลิงก์ (Anyone with the link)' เป็นสิทธิ์ ผู้มีสิทธิ์อ่าน นะครับ")
            return pd.DataFrame()

        # อ่านตารางข้อมูลดิบ
        df = pd.read_csv(StringIO(response.text), on_bad_lines='skip', engine='python', dtype=str)
        if df.empty:
            return pd.DataFrame()

        # ล้างช่องว่างหัวคอลัมน์
        df.columns = df.columns.str.strip()
        
        # บังคับชื่อคอลัมน์สำคัญให้ตรงกับระบบหลักเพื่อความแม่นยำ
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

        # ล้างช่องว่างในเซลล์ข้อมูลทั้งหมด
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

        # ฟังก์ชันแปลงวันที่ระบบโรงพยาบาล (รองรับ พ.ศ. / ค.ศ. และคัดกรองแถวสรุปยอดทิ้ง)
        def parse_date(row):
            date_val = str(row.get('ว/ด/ป', '')).strip()
            if not date_val or any(x in date_val.lower() for x in ['nan', 'null', 'total', 'summary', 'may', 'june']):
                return None
            try:
                if '/' in date_val:
                    parts = date_val.split('/')
                    if len(parts) == 3:
                        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                        if y > 2500: y -= 543  # แปลง พ.ศ. เป็น ค.ศ.
                        elif y < 100: y += 2000
                        
                        # ลองแปลงแบบ วัน/เดือน/ปี ถ้าไม่ได้ให้สลับเป็น เดือน/วัน/ปี
                        try:
                            return pd.Timestamp(year=y, month=m, day=d).date()
                        except:
                            return pd.Timestamp(year=y, month=d, day=m).date()
                return pd.to_datetime(date_val).date()
            except:
                return None

        df['Formatted_Date'] = df.apply(parse_date, axis=1)
        
        # ตัดแถวขยะที่ไม่มีวันที่ทิ้งทันที ป้องกันระบบปฏิทินค้าง
        df = df.dropna(subset=['Formatted_Date'])
        df = df[df['Topic/risk finding'] != ""]

        return df
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame()

def get_status_group(status_value):
    status_str = str(status_value).strip().lower()
    if any(x in status_str for x in ["เรียบร้อย", "complete", "เสร็จสิ้น", "สำเร็จ", "✅", "done"]):
        return "complete"
    elif any(x in status_str for x in ["on process", "onprocess", "กำลังทำ", "กำลังดำเนินการ", "🔄"]):
        return "on_process"
    else:
        return "pending"
