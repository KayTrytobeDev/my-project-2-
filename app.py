import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
from utils import load_data, get_status_group

st.set_page_config(page_title="FMS Risk Calendar", layout="wide")

# ดึงข้อมูลจากฐานข้อมูลชีตใหม่
df = load_data()

st.sidebar.title("📌 FMS Navigation")
menu = st.sidebar.radio("เลือกหน้าต่างการทำงาน", [
    "📅 ปฏิทินติดตามงาน (Calendar View)", 
    "📊 แดชบอร์ดสรุปผล (Dashboard)"
])

if menu == "📅 ปฏิทินติดตามงาน (Calendar View)":
    st.title("📅 ระบบปฏิทินติดตามประเด็นความเสี่ยง")
    
    if df.empty:
        st.info("💡 กำลังรอการเชื่อมต่อข้อมูลดิบ... หากระบบแสดงข้อความแจ้งเตือนด้านบน โปรดตรวจสอบสิทธิ์การแชร์ของ Google Sheet อีกครั้งครับ")
    else:
        # ตัวกรองข้อมูลความเสี่ยง
        col1, col2 = st.columns(2)
        with col1:
            user_list = ["ทั้งหมด"] + sorted(list(df['Responsible Person'].unique())) if 'Responsible Person' in df.columns else ["ทั้งหมด"]
            user_filter = st.selectbox("👤 เลือกกรองตามผู้รับผิดชอบ", user_list)
        with col2:
            status_filter = st.selectbox("🔄 เลือกกรองตามสถานะงาน", ["ทั้งหมด", "รอดำเนินการ", "กำลังดำเนินการ", "เรียบร้อย"])

        # กรองข้อมูลตารางตามเงื่อนไข
        filtered_df = df.copy()
        if 'Responsible Person' in filtered_df.columns and user_filter != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['Responsible Person'] == user_filter]
            
        if 'Status' in filtered_df.columns and status_filter != "ทั้งหมด":
            target = "complete" if status_filter == "เรียบร้อย" else "on_process" if status_filter == "กำลังดำเนินการ" else "pending"
            filtered_df = filtered_df[filtered_df['Status'].apply(get_status_group) == target]

        # เตรียมข้อมูลสลักลงหมุดปฏิทิน
        calendar_events = []
        for idx, row in filtered_df.iterrows():
            date_str = row['Formatted_Date'].strftime("%Y-%m-%d")
            status_type = get_status_group(row.get('Status', ''))
            
            # โทนสีแยกแยะตามสถานะ (เขียว ส้ม น้ำเงิน)
            color_map = {"complete": "#28a745", "on_process": "#fd7e14", "pending": "#007bff"}
            
            calendar_events.append({
                "title": f"[{row.get('Status', 'รอดำเนินการ')}] {row.get('Topic/risk finding')}",
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
        
        # แสดงผลตัวปฏิทินหลัก
        cal_output = calendar(events=calendar_events, options=calendar_options, key="fms_clean_calendar")
        
        # แสดงรายละเอียดด้านล่างปฏิทินเมื่อมีการกดคลิกที่หมุดกิจกรรม
        if cal_output.get("eventClick"):
            clicked_id = cal_output["eventClick"]["event"]["id"]
            case_data = df.loc[int(clicked_id)]
            
            st.markdown("---")
            st.subheader(f"🔍 รายละเอียดความเสี่ยง: {case_data.get('Topic/risk finding')}")
            
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.write(f"📅 **วันที่บันทึก:** {case_data.get('ว/ด/ป')}")
                st.write(f"🏢 **สถานที่เกิดเหตุ (Location):** {case_data.get('Location', 'ไม่ระบุสถานที่')}")
                st.write(f"👤 **ผู้รับผิดชอบหลัก:** {case_data.get('Responsible Person', 'ไม่ระบุ')}")
            with d_col2:
                st.write(f"🚦 **สถานะความคืบหน้า:** {case_data.get('Status', 'รอดำเนินการ')}")
                st.write(f"🔧 **แนวทางแก้ไข (Corrective Action):** {case_data.get('Corrective Action', '-')}")
                
                # ตรวจสอบและแสดงรูปภาพ Before/After
                img_b = case_data.get('Picture (before)', '')
                img_a = case_data.get('Picture (After)', '')
                if img_b and str(img_b).startswith('http'):
                    st.image(img_b, caption="🖼️ รูปภาพก่อนแก้ไข", use_container_width=True)
                if img_a and str(img_a).startswith('http'):
                    st.image(img_a, caption="✨ รูปภาพหลังแก้ไขเรียบร้อย", use_container_width=True)

elif menu == "📊 แดชบอร์ดสรุปผล (Dashboard)":
    st.title("📊 แดชบอร์ดสรุปสถิติ FMS Risk")
    if df.empty:
        st.info("💡 ไม่มีข้อมูลแสดงผลในส่วนแดชบอร์ด")
    else:
        df['status_group'] = df['Status'].apply(get_status_group)
        c1, c2, c3 = st.columns(3)
        c1.metric("🔴 เคสที่รอดำเนินการ", len(df[df['status_group'] == 'pending']))
        c2.metric("🟡 เคสที่กำลังทำ", len(df[df['status_group'] == 'on_process']))
        c3.metric("🟢 เคสที่เสร็จสิ้น", len(df[df['status_group'] == 'complete']))
        
        st.markdown("---")
        st.subheader("📋 ตารางข้อมูลสรุปภาพรวมทั้งหมด")
        display_cols = [c for c in ['ว/ด/ป', 'Topic/risk finding', 'Location', 'Responsible Person', 'Status'] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)
