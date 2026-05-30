import streamlit as st
import plotly.express as px
import datetime
import pandas as pd
import requests
from streamlit_calendar import calendar
from utils import load_data, get_status_group, convert_image_to_base64

st.set_page_config(page_title="FMS Risk & Corrective Tracker", layout="wide")

# ปรับเปลี่ยนสไตล์ CSS ให้เหมาะสม เรียบหรู คลีน สไตล์โรงพยาบาลและงานคุณภาพ
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSelectbox label, .stTextInput label, .stTextArea label, .stDateInput label, .stFileUploader label { font-size: 15px !important; font-weight: bold; color: #0F172A; }
    .card { background-color: white; padding: 22px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); margin-bottom: 15px; }
    .card-complete { border-left: 8px solid #10B981; }
    .card-on-process { border-left: 8px solid #3B82F6; }
    .card-pending { border-left: 8px solid #F59E0B; }
    
    .status-badge { padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; text-align: center; display: inline-block; }
    .badge-complete { background-color: #D1FAE5; color: #065F46; }
    .badge-on-process { background-color: #DBEAFE; color: #1E40AF; }
    .badge-pending { background-color: #FEF3C7; color: #92400E; }
    
    .risk-badge { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-left: 10px; color: white; }
    .risk-low { background-color: #10B981; }
    .risk-medium { background-color: #F59E0B; }
    .risk-high { background-color: #EF4444; }

    .form-container { background-color: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .metric-box { background-color: #F8FAFC; padding: 18px; border-radius: 10px; border: 1px solid #E2E8F0; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

try:
    df_all = load_data()
    
    # ดึงเฉพาะรายการข้อมูลที่เป็นประเด็นจริง (ไม่เอาแถวว่าง หรือข้อความทดสอบหลัก)
    if not df_all.empty and 'Topic/risk finding' in df_all.columns:
        df_raw = df_all[~df_all['Topic/risk finding'].astype(str).str.contains('ไม่พบประเด็น|ไม่มีประเด็น|Tester|test', na=False)]
        df_raw = df_raw[df_raw['Topic/risk finding'].astype(str).str.strip() != ""]
    else:
        df_raw = df_all.copy()

    st.sidebar.title("📌 เมนูควบคุมระบบ FMS")
    menu = st.sidebar.radio("เลือกโหมดการแสดงผล", [
        "📅 ปฏิทินติดตามงาน (FMS Round)", 
        "📊 สรุปภาพรวม (Dashboard)",
        "➕ บันทึกประเด็นความเสี่ยงเพิ่ม"
    ])

    if menu == "📅 ปฏิทินติดตามงาน (FMS Round)":
        st.title("📅 ระบบปฏิทินติดตามประเด็นความเสี่ยง (FMS Round)")
        
        # จัดเตรียมข้อมูลรายชื่อแผนก/ผู้รับผิดชอบ และสถานะจากตารางล่าสุด
        raw_owners = df_raw['Responsible Person'].unique().tolist() if 'Responsible Person' in df_raw.columns else []
        owners = ["ทั้งหมด"] + sorted([str(o).strip() for o in raw_owners if str(o).strip() != '' and str(o).lower() != 'nan'])
        
        raw_statuses = df_raw['Status'].unique().tolist() if 'Status' in df_raw.columns else []
        statuses = ["ทั้งหมด"] + sorted([str(s).strip() for s in raw_statuses if str(s).strip() != '' and str(s).lower() != 'nan'])

        f_col1, f_col2 = st.columns(2)
        with f_col1: sel_owner = st.selectbox("👤 กรองตามผู้รับผิดชอบ / แผนก", owners)
        with f_col2: sel_status = st.selectbox("🔘 กรองตามสถานะการแก้ไข", statuses)

        df_filtered = df_raw.copy()
        if sel_owner != "ทั้งหมด" and not df_filtered.empty:
            df_filtered = df_filtered[df_filtered['Responsible Person'].astype(str).str.strip() == str(sel_owner).strip()]
        if sel_status != "ทั้งหมด" and not df_filtered.empty:
            df_filtered = df_filtered[df_filtered['Status'].astype(str).str.strip() == str(sel_status).strip()]

        # เตรียมข้อมูลสำหรับหมุดปฏิทิน
        calendar_events = []
        if 'Formatted_Date' in df_filtered.columns and not df_filtered.empty:
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
        
        cal_data = calendar(events=calendar_events, options=calendar_options, key='fms_tracker_calendar')
        
        # ค้นหาเดือนปัจจุบันที่ผู้ใช้กำลังเปิดดูบนปฏิทินเพื่อสรุปยอดในแต่ละเดือน
        current_view_month = None
        if cal_data.get("view") and cal_data["view"].get("currentStart"):
            start_date_str = cal_data["view"]["currentStart"].split("T")[0]
            try: current_view_month = (pd.to_datetime(start_date_str) + datetime.timedelta(days=15)).month
            except: current_view_month = datetime.date.today().month
        else:
            current_view_month = datetime.date.today().month

        if 'Formatted_Date' in df_filtered.columns and not df_filtered.empty:
            df_filtered_clean = df_filtered[df_filtered['Formatted_Date'].notna() & (df_filtered['Formatted_Date'] != "")]
            df_filtered_clean['Month_Num'] = pd.to_datetime(df_filtered_clean['Formatted_Date']).dt.month
            monthly_count = len(df_filtered_clean[df_filtered_clean['Month_Num'] == current_view_month])
        else:
            monthly_count = 0

        months_th = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
        st.markdown(f"""
            <div class="metric-box">
                <span style="font-size: 15px; color: #64748B; font-weight: bold;">📊 จำนวนประเด็นความเสี่ยงรวมประจำเดือน {months_th[current_view_month]}</span><br>
                <span style="font-size: 30px; color: #0F172A; font-weight: 900;">{monthly_count} รายการ</span>
            </div>
        """, unsafe_allow_html=True)

        # จัดการแสดงการ์ดรายละเอียดเมื่อคลิกวันที่บนปฏิทิน
        selected_date = None
        if cal_data.get("eventClick"): selected_date = cal_data["eventClick"]["event"]["id"]
        elif cal_data.get("dateClick"): selected_date = cal_data["dateClick"]["date"].split("T")[0]
            
        if selected_date:
            st.success(f"📂 ข้อมูลประเด็นงานประจำวันที่ตรวจพบ: **{selected_date}**")
            df_display = df_filtered[df_filtered['Formatted_Date'].astype(str) == str(selected_date)] if 'Formatted_Date' in df_filtered.columns else pd.DataFrame()
            
            if not df_display.empty:
                st.divider()
                for idx, row in df_display.iterrows():
                    group = get_status_group(row.get('Status'))
                    card_style = "card card-complete" if group == "complete" else ("card card-on-process" if group == "on_process" else "card card-pending")
                    badge_html = f'<span class="status-badge badge-{group}">{row.get("Status", "รอดำเนินการ")}</span>'
                    
                    r_level = str(row.get('Risk Level', row.get('Risk', 'Low'))).strip()
                    if 'low' in r_level.lower() or 'ต่ำ' in r_level: risk_class = "risk-badge risk-low"
                    elif 'med' in r_level.lower() or 'กลาง' in r_level: risk_class = "risk-badge risk-medium"
                    elif 'high' in r_level.lower() or 'สูง' in r_level: risk_class = "risk-badge risk-high"
                    else: risk_class = "risk-badge risk-low"
                    
                    st.markdown(f"""
                        <div class="{card_style}">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin:0; color:#0F172A;">
                                    📍 {row.get('Topic/risk finding','ไม่มีชื่อประเด็น')}
                                    <span class="{risk_class}">⚠️ ความเสี่ยง: {r_level if r_level != "" else "Low"}</span>
                                </h3>
                                {badge_html}
                            </div>
                            <p style="font-size:14px; color:#475569; margin-top:6px;">🏢 <b>สถานที่ตรวจพบ:</b> {row.get('Location','ไม่ระบุ')} | 👤 <b>แผนกที่รับผิดชอบ:</b> {row.get('Responsible Person','ไม่ระบุ')}</p>
                            <p style="font-size:15px; background:#F8FAFC; padding:12px; border-radius:6px; border: 1px solid #E2E8F0;">🔧 <b>แนวทางแก้ไข (Corrective Action):</b> {row.get('Corrective Action','ไม่มีข้อมูลระบุไว้')}</p>
                            {"<p style='font-size:14px; color:#64748B;'>📝 <b>หมายเหตุ:</b> " + str(row.get('Remark')) + "</p>" if row.get('Remark') else ""}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # คอลัมน์แสดงรูปภาพเปรียบเทียบ ก่อน/หลัง แก้ไข
                    img_col1, img_col2 = st.columns(2)
                    with img_col1:
                        pic_b = str(row.get('Picture (before)', '')).strip().replace(" ", "")
                        if pic_b and (pic_b.startswith('data:image') or pic_b.startswith('http')):
                            st.image(pic_b, caption="📸 ภาพก่อนดำเนินแก้ไข (Before)", use_container_width=True)
                    with img_col2:
                        pic_a = str(row.get('Picture (After)', '')).strip().replace(" ", "")
                        if pic_a and (pic_a.startswith('data:image') or pic_a.startswith('http')):
                            st.image(pic_a, caption="✅ ภาพหลังดำเนินการแก้ไขสำเร็จ (After)", use_container_width=True)
                    st.divider()
            else:
                st.warning("ไม่พบรายการข้อมูลในวันที่เลือก")

    elif menu == "📊 สรุปภาพรวม (Dashboard)":
        st.title("📊 สรุปภาพรวมสถิติความเสี่ยง FMS Round")
        if not df_raw.empty:
            st.metric("รวมข้อมูลประเด็นความเสี่ยงสะสมในระบบ", f"{len(df_raw)} รายการ")
            
            c1, c2 = st.columns(2)
            with c1:
                if 'Responsible Person' in df_raw.columns:
                    st.plotly_chart(px.bar(df_raw, x='Responsible Person', color='Status', title="จำนวนประเด็นความเสี่ยงแบ่งแยกตาม แผนก/ผู้รับผิดชอบ"), use_container_width=True)
            with c2:
                if 'Status' in df_raw.columns:
                    st.plotly_chart(px.pie(df_raw, names='Status', hole=0.4, title="สัดส่วนความคืบหน้าของสถานะงานทั้งหมด"), use_container_width=True)

    elif menu == "➕ บันทึกประเด็นความเสี่ยงเพิ่ม":
        st.title("➕ บันทึกประเด็นความเสี่ยงใหม่ลงฐานข้อมูลสเปรดชีต")
        # เปลี่ยนเป็น URL ของ Google Apps Script ของคุณเพื่อรองรับโครงสร้างตารางนี้
        API_URL = "https://script.google.com/macros/s/AKfycbyb17lC8nve1YstfR-z6V2mD5q57_gRlygC-PzB9bI3z1fWp5tRE_X8k0_o_SgU66G3/exec"
        
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            with st.form("fms_add_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_date = st.date_input("📅 วัน/เดือน/ปี ที่ตรวจพบประเด็น", datetime.date.today())
                    new_topic = st.text_input("📍 ประเด็นความเสี่ยงที่พบ (Topic/risk finding)*")
                    new_location = st.text_input("🏢 สถานที่ (Location)")
                with col2:
                    new_owner = st.text_input("👤 ผู้รับผิดชอบ/แผนก (Responsible Person)*")
                    new_status = st.selectbox("🔘 สถานะงาน", ["คงค้าง", "กำลังดำเนินการ", "แก้ไขเรียบร้อยแล้ว"])
                    new_risk = st.selectbox("⚠️ ระดับความเสี่ยง (Risk Level)", ["Low", "Medium", "High"])
                
                new_action = st.text_area("🔧 แนวทางแก้ไข (Corrective Action)")
                new_remark = st.text_input("📝 หมายเหตุ (Remark)")
                st.markdown("---")
                
                col_img1, col_img2 = st.columns(2)
                with col_img1: up_before = st.file_uploader("📸 อัปโหลดภาพก่อนแก้ไข (Before)", type=["jpg","jpeg","png"])
                with col_img2: up_after = st.file_uploader("✅ อัปโหลดภาพหลังแก้ไข (After)", type=["jpg","jpeg","png"])
                
                if st.form_submit_button("💾 ส่งข้อมูลบันทึกลงตารางหลัก"):
                    if not new_topic or not new_owner:
                        st.error("❌ เกิดข้อผิดพลาด: จำเป็นต้องกรอก 'ประเด็นความเสี่ยง' และ 'ผู้รับผิดชอบ'")
                    else:
                        with st.spinner("กำลังบันทึกข้อมูลและอัปโหลดเข้าสู่ Google Sheet..."):
                            payload = {
                                "date_d": new_date.strftime("%Y-%m-%d"),
                                "topic": new_topic,
                                "location": new_location,
                                "owner": new_owner,
                                "status": new_status,
                                "risk_level": new_risk,
                                "action": new_action,
                                "remark": new_remark,
                                "pic_before": convert_image_to_base64(up_before),
                                "pic_after": convert_image_to_base64(up_after)
                            }
                            try:
                                res = requests.post(API_URL, json=payload)
                                if res.status_code == 200:
                                    st.success("🎉 บันทึกข้อมูลประเด็นความเสี่ยง FMS สำเร็จเรียบร้อยแล้ว!")
                                    st.balloons()
                                    st.cache_data.clear()
                                else:
                                    st.error(f"การเชื่อมต่อผิดพลาด รหัสสถานะ: {res.status_code}")
                            except Exception as err:
                                st.error(f"ไม่สามารถส่งข้อมูลไปยัง Server หลังบ้านได้: {err}")
            st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"ระบบขัดข้องในการโหลดหน้าเว็บ: {e}")
