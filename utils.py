import streamlit as st
import pandas as pd

@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    df = pd.read_csv(url)
    
    # Mapping คอลัมน์ตามลำดับตำแหน่งความปลอดภัย
    mapping = {}
    if len(df.columns) >= 2: mapping[df.columns[1]] = 'ว/ด/ป'
    if len(df.columns) >= 4: mapping[df.columns[3]] = 'Picture (before)'
    if len(df.columns) >= 5: mapping[df.columns[4]] = 'Picture (After)'
    if len(df.columns) >= 8: mapping[df.columns[7]] = 'Responsible Person'
    if len(df.columns) >= 9: mapping[df.columns[8]] = 'Status'
    
    for col in df.columns:
        if 'topic' in str(col).lower() or 'ประเด็น' in str(col):
            mapping[col] = 'Topic/risk finding'
        if 'location' in str(col).lower() or 'สถานที่' in str(col):
            mapping[col] = 'Location'
        if 'action' in str(col).lower() or 'แก้ไข' in str(col):
            mapping[col] = 'Corrective Action'

    df = df.rename(columns=mapping)
    
    for standard_col in ['ว/ด/ป', 'Picture (before)', 'Picture (After)', 'Responsible Person', 'Status', 'Topic/risk finding', 'Location', 'Corrective Action']:
        if standard_col not in df.columns:
            df[standard_col] = None

    # แปลงข้อมูลวันที่ให้ถูกต้องสมบูรณ์
    df['Formatted_Date'] = pd.to_datetime(df['ว/ด/ป'], errors='coerce').dt.date
    return df

def check_complete(status_text):
    if pd.isna(status_text):
        return False
    status_str = str(status_text).strip()
    return any(word in status_str for word in ["เรียบร้อย", "Complete", "complete", "เสร็จสิ้น", "สำเร็จ"])
