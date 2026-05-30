import streamlit as st
import plotly.express as px
import datetime
import pandas as pd
import requests
from streamlit_calendar import calendar
from utils import load_data, get_status_group, convert_image_to_base64

st.set_page_config(page_title="FMS Risk Tracker", layout="wide")

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
    
    .risk-badge { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-left: 10px; color: white; }
    .risk-low { background-color: #10B981; }
    .risk-medium { background-color: #F59E0B; }
    .risk-high { background-color: #EF4444; }

    .form-container { background-color: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .metric-box { background-color: #EEF2F6; padding: 15px; border-radius: 8px; border: 1px solid #CBD5E1; text-align: center; margin-bottom: 15px; }
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
        
        if not df_raw.empty:
            raw_owners = df_raw['Responsible Person'].unique().tolist() if 'Responsible Person' in df_raw.columns else []
            owners = ["ทั้งหมด"] + sorted([str(o).strip() for o in raw_owners if str(o).strip() != '' and str(o).lower() != 'nan'])
            
            raw_statuses = df_raw['Status'].unique().tolist() if 'Status' in df_raw.columns else []
            statuses = ["ทั้งหมด"] + sorted([str(s).strip() for s in raw_statuses if str(s).strip() != '' and str(s).lower() != 'nan'])
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
            df_with_date = df_filtered[df_filtered['Formatted_Date'].notna() & (df_filtered['Formatted_Date'] != "")]
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
        
        cal_data = calendar(events=calendar_events, options=calendar_options, key='risk_calendar_v11')
        
        current_view_month = None
        if cal_data.get("view") and cal_data["view"].get("currentStart"):
            start_date_str = cal_data["view"]["currentStart"].split("T")[0]
            try: current_view_month = (pd.to_datetime(start_date_str) + datetime.timedelta(days=15)).month
            except: current_view_month = datetime.date.today().month
        else:
            current_view_month = datetime.date.today().month

        if not df_filtered.empty and 'Formatted_Date' in df_filtered.columns:
            df_filtered_clean = df_filtered[df_filtered['Formatted_Date'].notna() & (df_filtered['Formatted_Date'] != "")]
            df_filtered_clean['Month_Num'] = pd.to_datetime(df_filtered_clean['Formatted_Date']).dt.month
            monthly_count = len(df_filtered_clean[df_filtered_clean['Month_Num'] == current_view_month])
        else:
            monthly_count = 0

        months_th = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
        st.markdown(f"""
            <div class="metric-box">
                <span style="font-size: 16px; color: #475569; font-weight: bold;">📊 จำนวนเคสทั้งหมดของเดือน {months_th[current_view_month]}</span><br>
                <span style="font-size: 28px; color: #1E3A8A; font-weight: 900;">{monthly_count} รายการ</span>
            </div>
        """, unsafe_allow_html=True)

        selected_date = None
        if cal_data.get("eventClick"): selected_date = cal_data["eventClick"]["event"]["id"]
        elif cal_data.get("dateClick"): selected_date = cal_data["dateClick"]["date"].split("T")[0]
            
        if selected_date:
            st.success(f"📂 กำลังแสดงข้อมูลประเด็นงานของวันที่: **{selected_date}**")
            df_display = df_filtered[df_filtered['Formatted_Date'].astype(str) == str(selected_date)] if 'Formatted_Date' in df_filtered.columns else pd.DataFrame()
            
            if not df_display.empty:
                st.divider()
                for idx, row in df_display.iterrows():
                    group = get_status_group(row.get('Status'))
                    card_style = "card card-complete" if group == "complete" else ("card card-on-process" if group == "on_process" else "card card-pending")
                    badge_html = f'<span class="status-badge badge-{group}">{row.get("Status", "รอดำเนินการ")}</span>'
                    
                    r_level = str(row.get('Risk Level', row.get('Risk Lvl', row.get('Risk', 'Low')))).strip()
                    if 'low' in r_level.lower() or 'ต่ำ' in r_level: risk_class = "risk-badge risk-low"
                    elif 'med' in r_level.lower() or 'กลาง' in r_level: risk_class = "risk-badge risk-medium"
                    elif 'high' in r_level.lower() or 'สูง' in r_level: risk_class = "risk-badge risk-high"
                    else: risk_class = "risk-badge risk-low"
                    
                    st.markdown(f"""
                        <div class="{card_style}">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin:0; color:#1E3A8A;">
                                    📍 {row.get('Topic/risk finding','N/A')}
                                    <span class="{risk_class}">⚠️ ระดับความเสี่ยง: {r_level if r_level != "" else "Low"}</span>
                                </h3>
                                {badge_html}
                            </div>
                            <p style="font-size:14px; color:#4B5563; margin-top:5px;">🏢 <b>สถานที่:</b> {row.get('Location','N/A')} | 👤 <b>ผู้รับผิดชอบ:</b> {row.get('Responsible Person','N/A')}</p>
                            <p style="font-size:15px; background:#f1f5f9; padding:10px; border-radius:5px;">🔧 <b>แนวทางแก้ไข:</b> {row.get('Corrective Action','ไม่มีข้อมูล')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    img_col1, img_col2 = st.columns(2)
                    with img_col1:
                        pic_b = str(row.get('Picture (before)', '')).strip().replace(" ", "")
                        if pic_b and (pic_b.startswith('data:image') or pic_b.startswith('http')):
                            st.image(pic_b, caption="📸 ภาพก่อนแก้ไข (Before)", use_container_width=True)
                    with img_col2:
                        pic_a = str(row.get('Picture (After)', '')).strip().replace(" ", "")
                        if pic_a and (pic_a.startswith('data:image') or pic_a.startswith('http')):
                            st.image(pic_a, caption="✅ ภาพหลังแก้ไข (After)", use_container_width=True)
                    st.divider()
            else:
                st.warning("ไม่มีข้อมูลที่ตรงเงื่อนไขการกรองในวันนี้")

    elif menu == "📊 สรุปภาพรวม (Dashboard)":
        st.title("📊 สรุปภาพรวมโครงการ (Dashboard)")
        if not df_raw.empty:
            df_dash = df_raw[df_raw['Topic/risk finding'] != ""].copy()
            # ยุบและคลีนค่าว่าง Null ออกไปเพื่อให้กราฟวงกลมแสดงผลเฉพาะกลุ่มที่มีอยู่จริงแบบคลีนๆ
            df_dash['Status'] = df_dash['Status'].replace(["", "null", "None"], "ไม่ระบุสถานะ")
            df_dash = df_dash[df_dash['Status'] != "ไม่ระบุสถานะ"]
            
            st.metric("รวมเคสทั้งหมดในระบบ", f"{len(df_dash)} รายการ")
            
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.bar(df_dash, x='Responsible Person', color='Status', title="ปริมาณงานแยกตามแผนก/บุคคล"), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(df_dash, names='Status', title="สัดส่วนสถานะการดำเนินงาน"), use_container_width=True)

    elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
        st.title("➕ บันทึกข้อมูลประเด็นความเสี่ยงลง Google Sheet")
        
        # 🔗 ใส่ URL ของ Web App Google Apps Script ที่ Deploy เวอร์ชันล่าสุดของคุณด้านล่างนี้ครับ
        API_URL = "https://script.google.com/macros/s/AKfycbyb17lC8nve1YstfR-z6V2mD5q57_gRlygC-PzB9bI3z1fWp5tRE_X8k0_o_SgU66G3/exec"
        
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            with st.form("risk_form_v11_submit", clear_on_submit=True):
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
                            payload = {
                                "date_day": new_date.strftime("%d"),
                                "date_month": new_date.strftime("%b"),
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
                                    st.success("🎉 บันทึกข้อมูลและรูปภาพสำเร็จเรียบร้อย!")
                                    st.balloons()
                                    st.cache_data.clear()
                                else:
                                    st.error(f"เกิดข้อผิดพลาดจาก Server: {res.status_code} (ตรวจสอบให้มั่นใจว่าได้ Deploy เว็บแอปเป็นเวอร์ชันล่าสุดและเปิดสาธารณะแล้ว)")
                            except Exception as err:
                                st.error(f"ไม่สามารถเชื่อมต่อไปยังหลังบ้านได้: {err}")
            st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดระบบ: {e}")
