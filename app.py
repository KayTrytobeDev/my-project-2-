import streamlit as st
import plotly.express as px
import datetime
import pandas as pd
import requests
from streamlit_calendar import calendar
from utils import load_data, get_status_group, convert_image_to_base64

st.set_page_config(page_title="FMS Risk Tracker", layout="wide")

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
        
        # จัดการรายชื่อผู้รับผิดชอบและสถานะให้สะอาด ไม่มีค่าว่างหลุดมาให้กดเลือก
        if not df_raw.empty:
            raw_owners = df_raw['Responsible Person'].unique().tolist() if 'Responsible Person' in df_raw.columns else []
            owners = ["ทั้งหมด"] + sorted([str(o).strip() for o in raw_owners if str(o).strip() != '' and str(o).lower() != 'nan' and str(o) != '0.0'])
            
            raw_statuses = df_raw['Status'].unique().tolist() if 'Status' in df_raw.columns else []
            statuses = ["ทั้งหมด"] + sorted([str(s).strip() for s in raw_statuses if str(s).strip() != '' and str(s).lower() != 'nan' and str(s) != '0.0'])
        else:
            owners, statuses = ["ทั้งหมด"], ["ทั้งหมด"]

        f_col1, f_col2 = st.columns(2)
        with f_col1: sel_owner = st.selectbox("👤 กรองตามผู้รับผิดชอบ", owners)
        with f_col2: sel_status = st.selectbox("🔘 กรองตามสถานะงาน", statuses)

        df_filtered = df_raw.copy() if not df_raw.empty else pd.DataFrame()
        if sel_owner != "ทั้งหมด" and not df_filtered.empty:
            df_filtered = df_filtered[df_filtered['Responsible Person'].astype(str).str.strip() == str(sel_owner).strip()]
        if sel_status != "ทั้งหมด" and not df_filtered.empty:
            df_filtered = df_filtered[df_filtered['Status'].astype(str).str.strip() == str(sel_status).strip()]

        calendar_events = []
        if not df_filtered.empty and 'Formatted_Date' in df_filtered.columns:
            df_with_date = df_filtered[df_filtered['Formatted_Date'].notna()]
            for idx, row in df_with_date.iterrows():
                topic_val = str(row.get('Topic/risk finding', '')).strip()
                group = get_status_group(row.get('Status'))
                date_str = str(row['Formatted_Date'])
                
                if group == "complete": bg_color = "#10B981"
                elif group == "on_process": bg_color = "#3B82F6"
                else: bg_color = "#F59E0B"
                
                calendar_events.append({
                    "title": f"📍 {topic_val}", "start": date_str, "end": date_str,
                    "backgroundColor": bg_color, "borderColor": bg_color, "allDay": True, "id": date_str
                })

        calendar_options = {
            "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,listMonth"},
            "initialView": "dayGridMonth", "locale": "th"
        }
        
        cal_data = calendar(events=calendar_events, options=calendar_options, key='risk_calendar_final_v3')
        
        current_view_month = datetime.date.today().month
        if cal_data.get("view") and cal_data["view"].get("currentStart"):
            start_date_str = cal_data["view"]["currentStart"].split("T")[0]
            try: current_view_month = (pd.to_datetime(start_date_str) + datetime.timedelta(days=15)).month
            except: pass

        if not df_filtered.empty and 'Formatted_Date' in df_filtered.columns:
            df_filtered_clean = df_filtered[df_filtered['Formatted_Date'].notna()]
            if not df_filtered_clean.empty:
                df_filtered_clean['Month_Num'] = pd.to_datetime(df_filtered_clean['Formatted_Date']).dt.month
                monthly_count = len(df_filtered_clean[df_filtered_clean['Month_Num'] == current_view_month])
            else: monthly_count = 0
        else: monthly_count = 0

        st.metric(label="📊 จำนวนเคสทั้งหมดของเดือนที่เลือก", value=f"{monthly_count} รายการ")

        selected_date = None
        if cal_data.get("eventClick"): selected_date = cal_data["eventClick"]["event"]["id"]
        elif cal_data.get("dateClick"): selected_date = cal_data["dateClick"]["date"].split("T")[0]
            
        if selected_date:
            st.info(f"📂 ประเด็นงานประจำวันที่: {selected_date}")
            df_display = df_filtered[df_filtered['Formatted_Date'].astype(str) == str(selected_date)] if 'Formatted_Date' in df_filtered.columns else pd.DataFrame()
            
            if not df_display.empty:
                for idx, row in df_display.iterrows():
                    with st.container(border=True):
                        st.subheader(f"📍 {row.get('Topic/risk finding','N/A')}")
                        col_info1, col_info2, col_info3 = st.columns(3)
                        with col_info1: st.write(f"🏢 **สถานที่:** {row.get('Location','N/A')}")
                        with col_info2: st.write(f"👤 **ผู้รับผิดชอบ:** {row.get('Responsible Person','N/A')}")
                        with col_info3: st.write(f"🔘 **สถานะ:** {row.get('Status','ไม่ระบุ')}")
                        
                        st.info(f"🔧 **แนวทางแก้ไข:** {row.get('Corrective Action','ไม่มีข้อมูล')}")
                        
                        img_col1, img_col2 = st.columns(2)
                        with img_col1:
                            pic_b = str(row.get('Picture (before)', '')).strip().replace(" ", "")
                            if pic_b and (pic_b.startswith('data:image') or pic_b.startswith('http')):
                                st.image(pic_b, caption="📸 ภาพก่อนแก้ไข (Before)", use_container_width=True)
                        with img_col2:
                            pic_a = str(row.get('Picture (After)', '')).strip().replace(" ", "")
                            if pic_a and (pic_a.startswith('data:image') or pic_a.startswith('http')):
                                st.image(pic_a, caption="✅ ภาพหลังแก้ไข (After)", use_container_width=True)
            else:
                st.warning("ไม่มีข้อมูลประเด็นความเสี่ยงในวันที่เลือก")

    elif menu == "📊 สรุปภาพรวม (Dashboard)":
        st.title("📊 สรุปภาพรวมโครงการ (Dashboard)")
        if not df_raw.empty:
            df_dash = df_raw[df_raw['Topic/risk finding'] != ""].copy()
            df_dash['Status'] = df_dash['Status'].replace(["", "null", "None"], "ไม่ระบุสถานะ")
            st.metric("รวมเคสทั้งหมดในระบบ", f"{len(df_dash)} รายการ")
            
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.bar(df_dash, x='Responsible Person', color='Status', title="ปริมาณงานแยกตามแผนก/บุคคล"), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(df_dash, names='Status', title="สัดส่วนสถานะการดำเนินงาน"), use_container_width=True)

    elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
        st.title("➕ บันทึกข้อมูลประเด็นความเสี่ยงลง Google Sheet")
        
        # 🔗 ยืนยันใช้งานด้วย URL เว็บแอปพลิเคชันจริงของโครงการคุณ Booska
        API_URL = "https://script.google.com/macros/s/AKfycbygCY04RIFRVrGnpLNfMi2S21C3wlzLepO705AqCgT7M1ayzKW-nnFSJ4_R_vqIQV0W/exec"
        
        with st.form("risk_form_v12_submit", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_date = st.date_input("📅 วันที่ตรวจพบ", datetime.date.today())
                new_topic = st.text_input("📍 ประเด็นความเสี่ยงที่พบ (Topic/risk finding)*")
                new_location = st.text_input("🏢 สถานที่ (Location)")
            with col2:
                new_owner = st.text_input("👤 ผู้รับผิดชอบ (Responsible Person)*")
                new_status = st.selectbox("🔘 สถานะงาน", ["ดําเนินการเรียบร้อย", "รอดำเนินการ", "กำลังดำเนินการ"])
                new_risk = st.selectbox("⚠️ ระดับความเสี่ยง (Risk Level)", ["Low", "Medium", "High"])
            
            new_action = st.text_area("🔧 แนวทางการจัดการแก้ไข (Corrective Action)")
            st.markdown("---")
            
            col_img1, col_img2 = st.columns(2)
            with col_img1: up_before = st.file_uploader("📸 ภาพก่อนแก้ไข (Before)", type=["jpg","jpeg","png"])
            with col_img2: up_after = st.file_uploader("✅ ภาพหลังแก้ไข (After)", type=["jpg","jpeg","png"])
            
            if st.form_submit_button("💾 ส่งข้อมูลบันทึกลงตารางหลัก"):
                if not new_topic or not new_owner:
                    st.error("❌ บันทึกไม่สำเร็จ: กรุณากรอกช่องประเด็นความเสี่ยงและผู้รับผิดชอบ")
                else:
                    with st.spinner("กำลังส่งข้อมูลไปยัง Google Sheet..."):
                        th_year = new_date.year + 543
                        str_date_combined = f"{new_date.month}/{new_date.day}/{th_year}"
                        
                        payload = {
                            "formatted_date": str_date_combined,
                            "topic": new_topic,
                            "location": new_location,
                            "owner": new_owner,
                            "status": new_status,
                            "risk_level": new_risk,
                            "action": new_action,
                            "pic_before": convert_image_to_base64(up_before),
                            "pic_after": convert_image_to_base64(up_after)
                        }
                        try:
                            res = requests.post(API_URL, json=payload)
                            if res.status_code == 200:
                                st.success("🎉 บันทึกข้อมูลและรูปภาพขึ้นชีทสำเร็จเรียบร้อย!")
                                st.balloons()
                                st.cache_data.clear()
                            else:
                                st.error(f"เกิดข้อผิดพลาดจาก Server: {res.status_code}")
                        except Exception as err:
                            st.error(f"ไม่สามารถเชื่อมต่อไปยังหลังบ้านได้: {err}")

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดระบบ: {e}")
