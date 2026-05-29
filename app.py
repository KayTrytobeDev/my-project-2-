import streamlit as st
import plotly.express as px
import datetime
import pandas as pd
import requests
from streamlit_calendar import calendar
from utils import load_data, get_status_group, convert_image_to_base64

st.set_page_config(page_title="Corrective Action Tracker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSelectbox label, .stTextInput label, .stTextArea label, .stDateInput label, .stFileUploader label { font-size: 15px !important; font-weight: bold; color: #1E3A8A; }
    .card {
        background-color: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px;
    }
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
        st.write("💡 *คลิกเลือกกล่องสีบนหน้าปฏิทิน เพื่อดึงรูปภาพและรายละเอียดงานมาตรวจสอบด้านล่าง*")
        
        raw_owners = df_raw['Responsible Person'].dropna().astype(str).unique().tolist() if 'Responsible Person' in df_raw.columns else []
        owners = ["ทั้งหมด"] + sorted([o for o in raw_owners if o.strip() != ''])
        
        raw_statuses = df_raw['Status'].dropna().astype(str).unique().tolist() if 'Status' in df_raw.columns else []
        statuses = ["ทั้งหมด"] + sorted([s for s in raw_statuses if s.strip() != ''])

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
        
        cal_data = calendar(events=calendar_events, options=calendar_options, key='risk_calendar_final_v2')
        
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
                    
                    if group == "complete":
                        card_style, badge_html = "card card-complete", '<span class="status-badge badge-complete">✅ เรียบร้อย</span>'
                    elif group == "on_process":
                        card_style, badge_html = "card card-on-process", '<span class="status-badge badge-on-process">⏳ On process</span>'
                    else:
                        card_style, badge_html = "card card-pending", '<span class="status-badge badge-pending">📌 รอดำเนินการ</span>'
                    
                    with st.container():
                        st.markdown(f"""
                            <div class="{card_style}">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h3 style="margin:0; color:#1E3A8A;">📍 {row.get('Topic/risk finding') or 'ไม่ระบุหัวข้อ'}</h3>
                                    {badge_html}
                                </div>
                                <p style="font-size:15px; margin-top:8px; color: #4B5563;">
                                    <b>สถานที่:</b> {row.get('Location') or 'N/A'} | <b>ผู้รับผิดชอบ:</b> {row.get('Responsible Person') or 'N/A'}
                                </p>
                                <p style="font-size:15px;"><b>แนวทางการแก้ไข:</b> {row.get('Corrective Action') or 'ไม่มีข้อมูล'}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # 📸 ท่อนดึงและแสดงผลรูปภาพแก้ไขปัญหารูปไม่ขึ้น
                        img_col1, img_col2 = st.columns(2)
                        with img_col1:
                            st.caption("📸 ภาพก่อนแก้ไข (Before)")
                            pic_before = row.get('Picture (before)')
                            if pd.notna(pic_before):
                                pic_before_str = str(pic_before).strip().replace(" ", "") # คลีนช่องว่างป้องกันรหัสรูปพัง
                                if pic_before_str.startswith('http') or pic_before_str.startswith('data:image'):
                                    st.image(pic_before_str, use_container_width=True)
                                
                        with img_col2:
                            st.caption("✅ ภาพหลังแก้ไข (After)")
                            pic_after = row.get('Picture (After)')
                            if pd.notna(pic_after):
                                pic_after_str = str(pic_after).strip().replace(" ", "")
                                if pic_after_str.startswith('http') or pic_after_str.startswith('data:image'):
                                    st.image(pic_after_str, use_container_width=True)
                            else:
                                st.info("💡 เคสนี้ยังไม่มีการแนบไฟล์ภาพรายงานผลหลังแก้ไข (After)")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.warning("ไม่มีข้อมูลที่ตรงเงื่อนไขการกรองในวันนี้")

    elif menu == "📊 สรุปภาพรวม (Dashboard)":
        st.title("📊 สรุปภาพรวมโครงการ (Dashboard)")
        if df_raw.empty:
            st.info("ไม่มีข้อมูลเพียงพอต่อการคำนวณสถิติ")
        else:
            total = len(df_raw)
            df_raw['status_group'] = df_raw['Status'].apply(get_status_group)
            done = (df_raw['status_group'] == 'complete').sum()
            on_process = (df_raw['status_group'] == 'on_process').sum()
            pending = total - done - on_process
            percent = (done / total) * 100 if total > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("งานทั้งหมด", f"{total} เคส")
            m2.metric("เสร็จสิ้นแล้ว (Complete)", f"{done} เคส", delta=f"{percent:.1f}%")
            m3.metric("กำลังทำ (On Process)", f"{on_process} เคส")
            m4.metric("คงค้าง (Pending)", f"{pending} เคส")
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                if 'Responsible Person' in df_raw.columns:
                    owner_counts = df_raw.groupby('Responsible Person').size().reset_index(name='จำนวนงาน')
                    fig_owner = px.bar(owner_counts, x='Responsible Person', y='จำนวนงาน', title="ปริมาณงานแยกตามผู้รับผิดชอบ", color_discrete_sequence=['#3B82F6'])
                    st.plotly_chart(fig_owner, use_container_width=True)
            with c2:
                status_counts = df_raw['status_group'].value_counts().reset_index(name='จำนวน')
                status_counts['status_group'] = status_counts['status_group'].replace({'complete': '✅ Complete', 'on_process': '⏳ On Process', 'pending': '📌 Pending'})
                fig_pie = px.pie(status_counts, values='จำนวน', names='status_group', title="สัดส่วนสถานะงานทั้งหมด", hole=0.4,
                                 color_discrete_sequence=['#10B981', '#3B82F6', '#F59E0B'])
                st.plotly_chart(fig_pie, use_container_width=True)

    elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
        st.title("➕ บันทึกข้อมูลประเด็นความเสี่ยงและรูปภาพ")
        
        # 🔗 [จุดแก้ไขสำคัญ]: วาง URL Web App ของ Google Apps Script ที่ก๊อปปี้มาลงในเครื่องหมายคำพูดแทนข้อความด้านล่างนี้ครับ
        API_URL = "https://script.google.com/macros/s/AKfycbwD8Eocb126-JHESCRVd4ljT61hliQzBKpuxa03Xkb1U9wJgmtRH6ABEmIJYCSyBZpZXA/exec"
        
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            with st.form("main_upload_form_v2", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_date = st.date_input("📅 วันที่บันทึกข้อมูล", datetime.date.today())
                    new_topic = st.text_input("📍 ประเด็นที่พบ/ความเสี่ยง (Topic)*")
                    new_location = st.text_input("🏢 สถานที่เกิดเหตุ (Location)")
                with col2:
                    new_owner = st.text_input("👤 ผู้รับผิดชอบงาน (Responsible)*")
                    new_status = st.selectbox("🔘 สถานะงาน", ["⏳ Pending", "🔄 On Process", "✅ Complete"])
                
                new_action = st.text_area("🔧 แนวทางการจัดการแก้ไข (Corrective Action)")
                st.markdown("---")
                
                img_col1, img_col2 = st.columns(2)
                with img_col1:
                    uploaded_before = st.file_uploader("📸 เลือกอัปโหลดรูปภาพ (Before)*", type=["png", "jpg", "jpeg"])
                with img_col2:
                    uploaded_after = st.file_uploader("✅ เลือกอัปโหลดรูปภาพ (After)", type=["png", "jpg", "jpeg"])
                
                submit_btn = st.form_submit_button("💾 บันทึกและส่งข้อมูลเข้า Google Sheet")
                
                if submit_btn:
                    if API_URL == "วาง_URL_WEB_APP_ที่นี่":
                        st.error("❌ ยังไม่ได้ใส่ลิงก์หลังบ้าน: กรุณานำ Web App URL มาใส่ในโค้ดไลน์ที่ 149 ก่อนกดส่งข้อมูลนะครับ")
                    elif not new_topic or not new_owner:
                        st.error("❌ บันทึกไม่สำเร็จ: กรุณากรอกช่องประเด็นความเสี่ยงและผู้รับผิดชอบงานให้ครบถ้วน")
                    else:
                        with st.spinner("กำลังแปลงรหัสรูปภาพและบันทึกข้อมูล..."):
                            base64_before = convert_image_to_base64(uploaded_before)
                            base64_after = convert_image_to_base64(uploaded_after)
                            
                            payload = {
                                "date": str(new_date),
                                "topic": new_topic,
                                "location": new_location,
                                "owner": new_owner,
                                "status": new_status,
                                "action": new_action,
                                "pic_before": base64_before,
                                "pic_after": base64_after
                            }
                            
                            try:
                                response = requests.post(API_URL, json=payload)
                                if response.status_code == 200:
                                    st.success("🎉 บันทึกข้อมูลและรูปภาพ Base64 ลง Google Sheet สำเร็จแล้วเรียบร้อย!")
                                    st.balloons()
                                    st.cache_data.clear() # ล้าง Cache หน้าปฏิทินทันที เพื่อให้แสดงข้อมูลใหม่
                                else:
                                    st.error(f"❌ บันทึกล้มเหลว ข้อผิดพลาดรหัส: {response.status_code}")
                            except Exception as req_err:
                                st.error(f"❌ ระบบไม่สามารถเชื่อมต่อไปยังสเปรดชีตได้: {req_err}")
            st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"แอปพลิเคชันขัดข้องชั่วคราว: {e}")
