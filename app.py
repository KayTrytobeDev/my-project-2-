import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
from utils import load_data, get_status_group, convert_image_to_base64

st.set_page_config(page_title="FMS Risk Calendar", layout="wide")

# เรียกใช้งานข้อมูลหลังบ้าน
df = load_data()

st.sidebar.title("📌 เมนูควบคุม")
menu = st.sidebar.radio("เลือกโหมดการแสดงผล", [
    "📅 ปฏิทินติดตามงาน (รายวัน)", 
    "📊 สรุปภาพรวม (Dashboard)", 
    "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก"
])

if menu == "📅 ปฏิทินติดตามงาน (รายวัน)":
    st.title("📅 ระบบปฏิทินติดตามประเด็นความเสี่ยง")
    
    if df.empty:
        st.info("💡 ขณะนี้ไม่มีข้อมูลแสดงผล หรือกรุณาตรวจสอบสิทธิ์การแชร์ลิงก์ Google Sheet ของคุณ")
    else:
        # ตัวกรองข้อมูลบนหน้าเว็บ
        col1, col2 = st.columns(2)
        with col1:
            all_users = ["ทั้งหมด"] + sorted(list(df['Responsible Person'].unique())) if 'Responsible Person' in df.columns else ["ทั้งหมด"]
            user_filter = st.selectbox("👤 กรองตามผู้รับผิดชอบ", all_users)
        with col2:
            status_filter = st.selectbox("🔄 กรองตามสถานะงาน", ["ทั้งหมด", "รอดำเนินการ", "กำลังดำเนินการ", "เรียบร้อย"])

        # กรองข้อมูลตามเงื่อนไขที่เลือก
        filtered_df = df.copy()
        if 'Responsible Person' in filtered_df.columns and user_filter != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['Responsible Person'] == user_filter]
        
        if 'Status' in filtered_df.columns and status_filter != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['Status'].apply(get_status_group) == (
                "complete" if status_filter == "เรียบร้อย" else 
                "on_process" if status_filter == "กำลังดำเนินการ" else "pending"
            )]

        # แปลงตารางให้ออกมาเป็นโครงสร้างของปฏิทิน Calendar Component
        calendar_events = []
        for idx, row in filtered_df.iterrows():
            if pd.notnull(row.get('Formatted_Date')):
                date_str = row['Formatted_Date'].strftime("%Y-%m-%d")
                status_type = get_status_group(row.get('Status', ''))
                
                # เปลี่ยนสีปักหมุดตามสถานะงาน
                color_map = {"complete": "#28a745", "on_process": "#fd7e14", "pending": "#007bff"}
                
                calendar_events.append({
                    "title": str(row.get('Topic/risk finding', 'ไม่ระบุประเด็น')),
                    "start": date_str,
                    "end": date_str,
                    "color": color_map.get(status_type, "#007bff"),
                    "id": str(idx)
                })

        calendar_options = {
            "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,listMonth"},
            "initialView": "dayGridMonth",
            "locale": "th"
        }
        
        # แสดงผลปฏิทินภาษาไทย
        st.markdown("""
            <style>
                .fc-header-toolbar { font-family: 'Helvetica Neue', Arial, sans-serif; }
                .fc-event-title { font-size: 14px !important; font-weight: bold !important; padding: 3px; }
            </style>
        """, unsafe_allow_html=True)
        
        cal_output = calendar(events=calendar_events, options=calendar_options, key="fms_calendar")
        
        # ระบบกดดูรายละเอียดเมื่อคลิกที่ปักหมุดในปฏิทิน
        if cal_output.get("eventClick"):
            clicked_id = cal_output["eventClick"]["event"]["id"]
            case_data = df.loc[int(clicked_id)]
            
            st.markdown("---")
            st.subheader(f"🔍 รายละเอียด: {case_data.get('Topic/risk finding')}")
            
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.write(f"📅 **วันที่ตรวจพบ:** {case_data.get('ว/ด/ป')}")
                st.write(f"👤 **ผู้รับผิดชอบ:** {case_data.get('Responsible Person', 'ไม่ได้ระบุ')}")
                st.write(f"🚦 **สถานะปัจจุบัน:** {case_data.get('Status', 'รอดำเนินการ')}")
            
            # ดึงรูปภาพ Before / After มาแสดงคู่กันในรายละเอียดด้านล่าง
            with d_col2:
                img_b = case_data.get('Picture (before)', '')
                img_a = case_data.get('Picture (After)', '')
                if img_b:
                    st.image(img_b, caption="🖼️ ภาพก่อนแก้ไข (Before)", use_container_width=True)
                if img_a:
                    st.image(img_a, caption="✨ ภาพหลังแก้ไข (After)", use_container_width=True)

elif menu == "📊 สรุปภาพรวม (Dashboard)":
    st.title("📊 แดชบอร์ดสรุปสถิติ FMS Risk")
    if df.empty:
        st.info("💡 ไม่มีข้อมูลดิบสำหรับการสรุปผลสถิติ")
    else:
        c1, c2, c3 = st.columns(3)
        df['status_group'] = df['Status'].apply(get_status_group)
        c1.metric("🔴 เคสที่รอดำเนินการ", len(df[df['status_group'] == 'pending']))
        c2.metric("🟡 เคสที่กำลังทำ", len(df[df['status_group'] == 'on_process']))
        c3.metric("🟢 เคสที่เสร็จสิ้น", len(df[df['status_group'] == 'complete']))
        st.dataframe(df[['ว/ด/ป', 'Topic/risk finding', 'Responsible Person', 'Status']], use_container_width=True)

elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
    st.title("➕ ฟอร์มส่งรายงานประเด็นความเสี่ยงเพิ่มเติม")
    st.info("✍️ ส่วนฟอร์มนี้สำหรับกรอกข้อมูลเพิ่มลง Google Sheet (คุณ Booska สามารถเขียนคำสั่ง Append เพิ่มเติมเชื่อมกับ Service Account ได้เลยครับ)")
