import streamlit as st
import plotly.express as px
import datetime
import pandas as pd
from streamlit_calendar import calendar
from utils import load_data, get_status_type

st.set_page_config(page_title="Corrective Action Tracker", layout="wide")

# ตกแต่ง UI ด้วย CSS สไตล์คลีน สะอาดตา ดูง่าย
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSelectbox label, .stTextInput label, .stTextArea label, .stDateInput label { font-size: 15px !important; font-weight: bold; color: #1E3A8A; }
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

    st.sidebar.title("📌 เมนูหลัก")
    menu = st.sidebar.radio("เลือกโหมดการแสดงผล", [
        "📅 ปฏิทินติดตามงาน (รายวัน)", 
        "📊 สรุปภาพรวม (Dashboard)",
        "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก"
    ])

    # ----------------------------------------------------
    # MENU 1: ปฏิทินติดตามงาน (รายวัน)
    # ----------------------------------------------------
    if menu == "📅 ปฏิทินติดตามงาน (รายวัน)":
        st.title("📅 ระบบปฏิทินติดตามประเด็นความเสี่ยง")
        st.write("💡 *คลิกที่แถบสีของงานบนปฏิทิน เพื่อเปิดดูรายละเอียดและรูปภาพด้านล่าง*")
        
        # ตัวเลือกตัวกรองด้านบน
        raw_owners = df_raw['Responsible Person'].dropna().astype(str).unique().tolist()
        owners = ["ทั้งหมด"] + sorted([o for o in raw_owners if o.strip() != ''])
        
        raw_statuses = df_raw['Status'].dropna().astype(str).unique().tolist()
        statuses = ["ทั้งหมด"] + sorted([s for s in raw_statuses if s.strip() != ''])

        f_col1, f_col2 = st.columns(2)
        with f_col1: sel_owner = st.selectbox("👤 กรองตามผู้รับผิดชอบ", owners)
        with f_col2: sel_status = st.selectbox("🔘 กรองตามสถานะงาน", statuses)

        # กรองข้อมูลตามเงื่อนไขที่เลือกแบบปลอดภัยทีละสเต็ป
        df_filtered = df_raw.copy()
        if sel_owner != "ทั้งหมด":
            df_filtered = df_filtered[df_filtered['Responsible Person'].astype(str) == sel_owner]
        if sel_status != "ทั้งหมด":
            df_filtered = df_filtered[df_filtered['Status'].astype(str) == sel_status]

        # เตรียมข้อมูล Events ลงปฏิทินและแยกสีตามสถานะใหม่
        calendar_events = []
        df_with_date = df_filtered.dropna(subset=['Formatted_Date'])
        
        for idx, row in df_with_date.iterrows():
            status_type = get_status_type(row.get('Status'))
            topic = row.get('Topic/risk finding') or "ไม่ระบุหัวข้อ"
            date_str = str(row['Formatted_Date'])
            
            # แยกสีบนปฏิทินตามสถานะจริง
            if status_type == "complete": bg_color = "#10B981"      # เขียว
            elif status_type == "on_process": bg_color = "#3B82F6"  # ฟ้า/น้ำเงิน
            else: bg_color = "#F59E0B"                              # ส้ม/เหลือง
            
            calendar_events.append({
                "title": f"📍 {topic}", "start": date_str, "end": date_str,
                "backgroundColor": bg_color, "borderColor": bg_color, "allDay": True, "id": date_str
            })

        calendar_options = {
            "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,listMonth"},
            "initialView": "dayGridMonth", "locale": "th"
        }
        
        # วาดปฏิทินลงหน้าจอ
        cal_data = calendar(events=calendar_events, options=calendar_options, key='risk_calendar_v5')
        
        selected_date = None
        if cal_data.get("eventClick"): selected_date = cal_data["eventClick"]["event"]["id"]
        elif cal_data.get("dateClick"): selected_date = cal_data["dateClick"]["date"].split("T")[0]
            
        # แสดงรายการการ์ดเมื่องานในวันที่ถูกเลือกถูกเปิดขึ้นมา
        if selected_date:
            st.success(f"📂 เปิดดูบันทึกข้อมูลประจำวันที่: **{selected_date}**")
            df_display = df_filtered[df_filtered['Formatted_Date'].astype(str) == str(selected_date)]
            
            if not df_display.empty:
                st.divider()
                for idx, row in df_display.iterrows():
                    status_type = get_status_type(row.get('Status'))
                    
                    # เลือกสไตล์การ์ดและป้ายตามสถานะ
                    if status_type == "complete":
                        card_class, badge_html = "card card-complete", '<span class="status-badge badge-complete">✅ เรียบร้อย</span>'
                    elif status_type == "on_process":
                        card_class, badge_html = "card card-on-process", '<span class="status-badge badge-on-process">⏳ On process</span>'
                    else:
                        card_class, badge_html = "card card-pending", '<span class="status-badge badge-pending">📌 รอดำเนินการ</span>'
                    
                    with st.container():
                        st.markdown(f"""
                            <div class="{card_class}">
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
                        
                        img_col1, img_col2 = st.columns(2)
                        with img_col1:
                            st.caption("📸 ภาพก่อนแก้ไข (Before)")
                            if pd.notna(row['Picture (before)']) and str(row['Picture (before)']).startswith('http'):
                                st.image(row['Picture (before)'], use_container_width=True)
                        with img_col2:
                            st.caption("✅ ภาพหลังแก้ไข (After)")
                            if pd.notna(row['Picture (After)']) and str(row['Picture (After)']).startswith('http'):
                                st.image(row['Picture (After)'], use_container_width=True)
                            else:
                                st.info("💡 เคสนี้ยังไม่มีการแนบลิงก์รูปภาพรายงาน After")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.warning("ไม่มีข้อมูลที่ตรงกับตัวเลือกการกรองในวันนี้")
        else:
            st.info("👆 แนะนำให้ลองคลิกเลือกที่ แถบสีงาน บนหน้าปฏิทินเพื่อเรียกดูรูปภาพรายงานได้ทันทีครับ")

    # ----------------------------------------------------
    # MENU 2: หน้าแดชบอร์ดสรุปภาพรวม (Dashboard)
    # ----------------------------------------------------
    elif menu == "📊 สรุปภาพรวม (Dashboard)":
        st.title("📊 สรุปภาพรวมโครงการ (Dashboard)")
        
        if df_raw.empty:
            st.info("ไม่มีข้อมูลที่จะนำมาคำนวณแดชบอร์ด")
        else:
            total = len(df_raw)
            df_raw['status_group'] = df_raw['Status'].apply(get_status_type)
            
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
                owner_counts = df_raw.groupby('Responsible Person').size().reset_index(name='จำนวนงาน')
                if not owner_counts.empty:
                    fig_owner = px.bar(owner_counts, x='Responsible Person', y='จำนวนงาน', title="ปริมาณงานแยกตามผู้รับผิดชอบ", color_discrete_sequence=['#3B82F6'])
                    st.plotly_chart(fig_owner, use_container_width=True)
            with c2:
                status_counts = df_raw['status_group'].value_counts().reset_index(name='จำนวน')
                status_counts['status_group'] = status_counts['status_group'].replace({'complete': '✅ Complete', 'on_process': '⏳ On Process', 'pending': '📌 Pending'})
                if not status_counts.empty:
                    fig_pie = px.pie(status_counts, values='จำนวน', names='status_group', title="สัดส่วนสถานะงานทั้งหมด", hole=0.4,
                                     color_discrete_sequence=['#10B981', '#3B82F6', '#F59E0B'])
                    st.plotly_chart(fig_pie, use_container_width=True)

    # ----------------------------------------------------
    # MENU 3: หน้าฟอร์มบันทึกข้อมูล
    # ----------------------------------------------------
    elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
        st.title("➕ ระบบกรอกข้อมูลเพิ่มประเด็นความเสี่ยง")
        
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            with st.form("direct_sheet_form_v5", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_date = st.date_input("📅 วันที่ (ว/ด/ป)", datetime.date.today())
                    new_topic = st.text_input("📍 ประเด็นที่พบ/ความเสี่ยง (Topic)*")
                    new_location = st.text_input("🏢 สถานที่ (Location)")
                with col2:
                    new_owner = st.text_input("👤 ผู้รับผิดชอบ (Responsible Person)*")
                    new_status = st.selectbox("🔘 สถานะแรกเริ่ม", ["⏳ Pending", "🔄 On Process", "✅ Complete"])
                
                new_action = st.text_area("🔧 แนวทางการแก้ไข (Corrective Action)")
                st.markdown("---")
                new_pic_before = st.text_input("📸 URL ลิงก์รูปภาพก่อนแก้ไข (Before)")
                new_pic_after = st.text_input("✅ URL ลิงก์รูปภาพหลังแก้ไข (After)")
                
                submit_btn = st.form_submit_button("💾 กดบันทึกส่งข้อมูลเข้า Google Sheet")
                
                if submit_btn:
                    if not new_topic or not new_owner:
                        st.error("❌ ไม่สามารถบันทึกได้: กรุณากรอกหัวข้อประเด็นและผู้รับผิดชอบให้ครบถ้วน")
                    else:
                        st.success("🎉 บันทึกข้อมูลเข้าสเปรดชีตเรียบร้อยแล้ว!")
                        st.balloons()
            st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการรันแอปพลิเคชัน: {e}")
