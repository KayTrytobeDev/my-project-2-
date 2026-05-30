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
        
        # ตรวจสอบหาคอลัมน์ประเด็นความเสี่ยง
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

        # ฟังก์ชันแกะอ่านค่า วันเดือนปี จากคอลัมน์เดียวของโรงพยาบาล (รองรับรูปแบบ 5/19/2569)
        def parse_hospital_date(row):
            try:
                date_col = 'ว/ด/ป' if 'ว/ด/ป' in df.columns else ('Date' if 'Date' in df.columns else df.columns[1])
                date_val = str(row.get(date_col, '')).strip()
                
                if not date_val or date_val.lower() == 'nan' or date_val == "":
                    return None
                
                if '/' in date_val:
                    parts = date_val.split('/')
                    year_val = int(parts[2])
                    # หากเป็นระบบปี พ.ศ. ให้แปลงเป็น ค.ศ. สำหรับระบบปฏิทิน Python (2569 -> 2026)
                    if year_val > 2500:
                        year_val = year_val - 543
                    
                    if int(parts[0]) > 12: # รูปแบบ วัน/เดือน/ปี
                        return pd.Timestamp(year=year_val, month=int(parts[1]), day=int(parts[0])).date()
                    else: # รูปแบบ เดือน/วัน/ปี
                        return pd.Timestamp(year=year_val, month=int(parts[0]), day=int(parts[1])).date()
                return None
            except:
