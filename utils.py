import streamlit as st
import pandas as pd

# ฟังก์ชันดึงข้อมูลจาก Google Sheet (แปลง Link เป็น Export CSV)
@st.cache_data(ttl=600)  # รีเฟรชข้อมูลใหม่ทุกๆ 10 นาที
def load_data():
    sheet_id = "1c2sJ3uDxUa39ARePd-Ry7Z5p3ZhqQYgyXTr2gLYSqaU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()  # ล้างช่องว่างของชื่อ Column
    return df

# ฟังก์ชันเช็กสถานะงาน (คืนค่า True ถ้า Complete)
def check_complete(status_text):
    status_str = str(status_text)
    return any(word in status_str for word in ["เรียบร้อย", "Complete", "complete"])
