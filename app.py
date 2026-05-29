import streamlit as st
import plotly.express as px
import datetime
import pandas as pd
import requests
from streamlit_calendar import calendar
from utils import load_data, get_status_group, convert_image_to_base64

st.set_page_config(page_title="Risk & Corrective Tracker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSelectbox label, .stTextInput label, .stTextArea label, .stDateInput label, .stFileUploader label { font-size: 15px !important; font-weight: bold; color: #1E3A8A; }
    .card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .card-complete { border-left: 8px solid #10B981; }
    .card-on-process { border-left: 8px solid #3B82F6; }
    .card-pending { border-left: 8px solid #F59E0B; }
    .status-badge { padding: 5px 12px; border-radius: 15px; font-weight: bold; font-size: 13px; }
    .badge-complete { background-color: #D1FAE5; color: #065F46; }
    .badge-on-process { background-color: #DBEAFE; color: #1E40AF; }
    .badge-pending { background-color: #FEF3C7; color: #92400E; }
    .form-container { background-color: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

try:
    df_raw = load_data()

    st.sidebar.title("📌 เมนูควบคุม")
    menu = st.sidebar.radio("เลือกโหมดการแสดงผล", [
        "📅 ปฏิทินติดตามงาน (รายวัน)", 
        "📊 สรุปภาพรวม (Dashboard)",
        "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก"
    ])

    if menu == "📅 ปฏิทินติดตามงาน (รายวัน)":
        st.title("📅 ระบบปฏิทินติดตามประเด็นความเสี่ยง")
        
        raw_owners = df_raw['Responsible Person'].dropna().unique().tolist() if 'Responsible Person' in df_raw.columns else []
        owners = ["ทั้งหมด"] + sorted([o for o in raw_owners if str(o).strip() != ''])
        
        raw_statuses = df_raw['Status'].dropna().unique().tolist() if 'Status' in df_raw.columns else []
        statuses = ["ทั้งหมด"] + sorted([s for s in raw_statuses if str(s).strip() != ''])

        f_col1, f_col2 = st.columns(2)
        with f_col1: sel_owner = st.selectbox("👤 กรองตามผู้รับผิดชอบ", owners)
        with f_col2: sel_status = st.selectbox("🔘 กรองตามสถานะงาน", statuses)

        df_filtered = df_raw.copy()
        if sel_owner != "ทั้งหมด" and not df_filtered.empty:
            df_filtered = df_filtered[df_filtered['Responsible Person'].astype(str) == sel_owner]
        if sel_status != "ทั้งหมด" and not df_filtered.empty:
            df_filtered = df_filtered[df_filtered['Status'].astype(str) == sel_status]

        calendar_events = []
        if 'Formatted_Date' in df_filtered.columns:
            df_with_date = df_filtered.dropna(subset=['Formatted_Date'])
            for idx, row in df_with_date.iterrows():
                group = get_status_group(row.get('Status'))
                topic = row.get('Topic/risk finding') or "ไม่ระบุหัวข้อ"
                date_str = str(row['Formatted_Date'])
                
                if group == "complete": bg_color = "#10B981"
                elif group == "on_process": bg_color = "#3B82F6"
                else: bg_color = "#F59E0B"
                
                calendar_events.append({
                    "title": f"📍 {topic}", "start": date_str, "end": date_str,
                    "backgroundColor": bg_color, "borderColor": bg_color, "allDay": True, "id": date_str
                })

        calendar_options = {
            "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,listMonth"},
            "initialView": "dayGridMonth", "locale": "th"
        }
        
        cal_data = calendar(events=calendar_events, options=calendar_options, key='risk_calendar_prod')
        
        selected_date = None
        if cal_data.get("eventClick"): selected_date = cal_data["eventClick"]["event"]["id"]
        elif cal_data.get("dateClick"): selected_date = cal_data["dateClick"]["date"].split("T")[0]
            
        if selected_date:
            st.success(f"📂 กำลังแสดงข้อมูลประจำวันที่: **{selected_date}**")
            df_display = df_filtered[df_filtered['Formatted_Date'].astype(str) == str(selected_date)] if 'Formatted_Date' in df_filtered.columns else pd.DataFrame()
            
            if not df_display.empty:
                st.divider()
                for idx, row in df_display.iterrows():
                    group = get_status_group(row.get('Status'))
                    card_style = "card card-complete" if group == "complete" else ("card card-on-process" if group == "on_process" else "card card-pending")
                    badge_html = f'<span class="status-badge badge-{group}">{row.get("Status", "Pending")}</span>'
                    
                    st.markdown(f"""
                        <div class="{card_style}">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin:0; color:#1E3A8A;">📍 {row.get('Topic/risk finding','N/A')}</h3>
                                {badge_html}
                            </div>
                            <p style="font-size:14px; color:#4B5563; margin-top:5px;">🏢 <b>สถานที่:</b> {row.get('Location','N/A')} | 👤 <b>ผู้รับผิดชอบ:</b> {row.get('Responsible Person','N/A')}</p>
                            <p style="font-size:15px; background:#f1f5f9; padding:10px; border-radius:5px;">🔧 <b>แนวทางแก้ไข:</b> {row.get('Corrective Action','ไม่มีข้อมูล')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # แสดงผลรูปภาพแบบล้างช่องว่าง (Base64 Safe-Render)
                    img_col1, img_col2 = st.columns(2)
                    with img_col1:
                        pic_b = str(row.get('Picture (before)', '')).strip().replace(" ", "")
                        if pic_b and (pic_b.startswith('data:image') or pic_b.startswith('http')):
                            st.image(pic_b, caption="📸 ภาพก่อนแก้ไข (Before)", use_container_width=True)
                    with img_col2:
                        pic_a = str(row.get('Picture (After)', '')).strip().replace(" ", "")
                        if pic_a and (pic_a.startswith('data:image') or pic_a.startswith('http')):
                            st.image(pic_a, caption="✅ ภาพหลังแก้ไข (After)", use_container_width=True)
                    st.markdown("<br>", unsafe_allow_html=True)

    elif menu == "📊 สรุปภาพรวม (Dashboard)":
        st.title("📊 สรุปภาพรวมโครงการ (Dashboard)")
        if not df_raw.empty:
            df_raw['group'] = df_raw['Status'].apply(get_status_group)
            st.metric("รวมเคสทั้งหมด", f"{len(df_raw)} รายการ")
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.bar(df_raw, x='Responsible Person', title="งานแยกตามบุคคล"), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(df_raw, names='Status', title="สัดส่วนสถานะ"), use_container_width=True)

    elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
        st.title("➕ บันทึกข้อมูลประเด็นความเสี่ยงลง Google Sheet")
        
        # 🔗 [จุดใส่ลิงก์]: นำ URL Web App จาก Google Apps Script มาใส่ตรงนี้แทนคำว่า "วาง_URL_ตรงนี้"
        API_URL = "วาง_URL_ตรงนี้"
        
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            with st.form("risk_form_v3", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_date = st.date_input("📅 วันที่ตรวจพบ", datetime.date.today())
                    new_topic = st.text_input("📍 ประเด็นความเสี่ยงที่พบ (Topic/risk finding)*")
                    new_location = st.text_input("🏢 สถานที่ (Location)")
                with col2:
                    new_owner = st.text_input("👤 ผู้รับผิดชอบ (Responsible Person)*")
                    new_status = st.selectbox("🔘 สถานะงาน", ["รอดำเนินการ", "กำลังดำเนินการ", "เรียบร้อย"])
                
                new_action = st.text_area("🔧 แนวทางการจัดการแก้ไข (Corrective Action)")
                st.markdown("---")
                
                col_img1, col_img2 = st.columns(2)
                with col_img1: up_before = st.file_uploader("📸 ภาพก่อนแก้ไข (Before)", type=["jpg","jpeg","png"])
                with col_img2: up_after = st.file_uploader("✅ ภาพหลังแก้ไข (After)", type=["jpg","jpeg","png"])
                
                if st.form_submit_button("💾 ส่งข้อมูลบันทึกลงตารางหลัก"):
                    if API_URL == "วาง_URL_ตรงนี้":
                        st.error("❌ กรุณาตั้งค่า URL Web App ที่บรรทัด 141 ก่อนใช้งานครับ")
                    elif not new_topic or not new_owner:
                        st.error("❌ บันทึกไม่สำเร็จ: กรุณากรอกช่องประเด็นความเสี่ยงและผู้รับผิดชอบ")
                    else:
                        with st.spinner("กำลังจัดฟอร์แมตข้อมูลส่งไปยัง Google Sheet..."):
                            payload = {
                                "date_d": new_date.strftime("%d"),
                                "date_m": new_date.strftime("%B"),
                                "topic": new_topic,
                                "location": new_location,
                                "owner": new_owner,
                                "status": new_status,
                                "action": new_action,
                                "pic_before": convert_image_to_base64(up_before),
                                "pic_after": convert_image_to_base64(up_after)
                            }
                            try:
                                res = requests.post(API_URL, json=payload)
                                if res.status_code == 200:
                                    st.success("🎉 บันทึกข้อมูลและรูปภาพลงล็อกตามคอลัมน์สเปรดชีตเรียบร้อย!")
                                    st.balloons()
                                    st.cache_data.clear()
                                else:
                                    st.error(f"เกิดข้อผิดพลาดจากฝั่ง Server: {res.status_code}")
                            except Exception as err:
                                st.error(f"ไม่สามารถเชื่อมต่อไปยังหลังบ้านได้: {err}")
            st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดระบบ: {e}")
