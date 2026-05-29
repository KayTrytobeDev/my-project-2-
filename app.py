import streamlit as st
import plotly.express as px
import datetime
import pandas as pd
from streamlit_calendar import calendar
from utils import load_data, check_complete

st.set_page_config(page_title="Corrective Action Tracker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSelectbox label, .stTextInput label, .stTextArea label, .stDateInput label { font-size: 16px !important; font-weight: bold; color: #1E3A8A; }
    .card {
        background-color: white; padding: 22px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px; border-left: 8px solid #3B82F6;
    }
    .complete-card { border-left: 8px solid #10B981 !important; }
    .status-badge { padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 14px; }
    .status-complete { background-color: #D1FAE5; color: #065F46; }
    .status-pending { background-color: #FEF3C7; color: #92400E; }
    .form-container { background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
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

    if menu == "📅 ปฏิทินติดตามงาน (รายวัน)":
        st.title("📅 ระบบปฏิทินติดตามประเด็นความเสี่ยง")
        st.write("💡 *คลิกเลือกวันที่หรือแถบสีงานบนปฏิทิน เพื่อเรียกเปิดดูรายละเอียดภาพประกอบ Before & After*")
        
        # คัดกรองตัวเลือกเมนู Dropdown
        raw_owners = df_raw['Responsible Person'].dropna().astype(str).unique().tolist()
        owners = ["ทั้งหมด"] + sorted([o for o in raw_owners if o.strip() != ''])
        
        raw_statuses = df_raw['Status'].dropna().astype(str).unique().tolist()
        statuses = ["ทั้งหมด"] + sorted([s for s in raw_statuses if s.strip() != ''])

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            sel_owner = st.selectbox("👤 กรองตามผู้รับผิดชอบ", owners)
        with f_col2:
            sel_status = st.selectbox("🔘 กรองตามสถานะงาน", statuses)

        # 🛠️ แยกชุดกรองข้อมูลทีละสเต็ป (แก้ปัญหา Ambiguous Error อย่างเด็ดขาด)
        df_filtered = df_raw.copy()
        if sel_owner != "ทั้งหมด":
            df_filtered = df_filtered[df_filtered['Responsible Person'].astype(str) == sel_owner]
        if sel_status != "ทั้งหมด":
            df_filtered = df_filtered[df_filtered['Status'].astype(str) == sel_status]

        # ประกอบกิจกรรมส่งให้ปฏิทิน
        calendar_events = []
        df_with_date = df_filtered.dropna(subset=['Formatted_Date'])
        
        for idx, row in df_with_date.iterrows():
            is_done = check_complete(row.get('Status'))
            topic = row.get('Topic/risk finding') or "ไม่ระบุหัวข้อ"
            date_str = str(row['Formatted_Date'])
            bg_color = "#10B981" if is_done else "#F59E0B"
            
            calendar_events.append({
                "title": f"📍 {topic}", 
                "start": date_str, 
                "end": date_str,
                "backgroundColor": bg_color, 
                "borderColor": bg_color, 
                "allDay": True, 
                "id": date_str
            })

        calendar_options = {
            "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,listMonth"},
            "initialView": "dayGridMonth", 
            "locale": "th"
        }
        
        # แสดงปฏิทิน
        cal_data = calendar(events=calendar_events, options=calendar_options, key='risk_calendar_v4')
        
        selected_date = None
        if cal_data.get("eventClick"): 
            selected_date = cal_data["eventClick"]["event"]["id"]
        elif cal_data.get("dateClick"): 
            selected_date = cal_data["dateClick"]["date"].split("T")[0]
            
        if selected_date:
            st.success(f"📂 เปิดดูบันทึกข้อมูลประจำวันที่: **{selected_date}**")
            df_display = df_filtered[df_filtered['Formatted_Date'].astype(str) == str(selected_date)]
            
            if not df_display.empty:
                st.divider()
                for idx, row in df_display.iterrows():
                    is_complete = check_complete(row.get('Status'))
                    card_class = "card complete-card" if is_complete else "card"
                    status_html = '<span class="status-badge status-complete">✅ เรียบร้อย</span>' if is_complete else '<span class="status-badge status-pending">⏳ กำลังดำเนินการ</span>'
                    
                    with st.container():
                        st.markdown(f"""
                            <div class="{card_class}">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h3 style="margin:0; color:#1E3A8A;">📍 {row.get('Topic/risk finding') or 'ไม่ระบุหัวข้อ'}</h3>
                                    {status_html}
                                </div>
                                <p style="font-size:16px; margin-top:8px; color: #4B5563;">
                                    <b>สถานที่:</b> {row.get('Location') or 'N/A'} | <b>ผู้รับผิดชอบ:</b> {row.get('Responsible Person') or 'N/A'}
                                </p>
                                <p style="font-size:16px;"><b>แนวทางการแก้ไข:</b> {row.get('Corrective Action') or 'ไม่มีข้อมูล'}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        img_col1, img_col2 = st.columns(2)
                        with img_col1:
                            st.caption("📸 ภาพก่อนแก้ไข (Before)")
                            if pd.notna(row['Picture (before)']) and str(row['Picture (before)']).startswith('http'):
                                st.image(row['Picture (before)'], use_container_width=True)
                        with img_col2:
                            st.caption("✅ ภาพหลังแก้ไข (After)")
                            if is_complete and pd.notna(row['Picture (After)']) and str(row['Picture (After)']).startswith('http'):
                                st.image(row['Picture (After)'], use_container_width=True)
                            elif not is_complete:
                                st.info("💡 เคสนี้อยู่ในระหว่างการดำเนินงาน (ยังไม่มีภาพแนบรายงาน After)")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.warning("ไม่มีข้อมูลที่ตรงกับตัวเลือกการกรองในวันนี้")
        else:
            st.info("👆 คุณสามารถกดคลิกแถบสีงานบนปฏิทินเพื่อเรียกดูรูปภาพรายงานได้ทันทีครับ")

    elif menu == "📊 สรุปภาพรวม (Dashboard)":
        st.title("📊 สรุปภาพรวมโครงการ (Dashboard)")
        
        if df_raw.empty:
            st.info("ไม่มีข้อมูลเพียงพอต่อการคำนวณแดชบอร์ด")
        else:
            total = len(df_raw)
            done = df_raw['Status'].apply(check_complete).sum()
            pending = total - done
            percent = (done / total) * 100 if total > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("งานทั้งหมด", f"{total} เคส")
            m2.metric("เสร็จสิ้นแล้ว", f"{done} เคส", delta=f"{percent:.1f}%")
            m3.metric("คงค้างอยู่", f"{pending} เคส", delta_color="inverse")
            m4.metric("จำนวนผู้รับผิดชอบ", df_raw['Responsible Person'].dropna().nunique())
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                owner_counts = df_raw.groupby('Responsible Person').size().reset_index(name='จำนวนงาน')
                if not owner_counts.empty:
                    fig_owner = px.bar(owner_counts, x='Responsible Person', y='จำนวนงาน', title="ปริมาณงานแยกตามผู้รับผิดชอบ", color_discrete_sequence=['#3B82F6'])
                    st.plotly_chart(fig_owner, use_container_width=True)
            with c2:
                df_raw['📊 กลุ่มสถานะ'] = df_raw['Status'].apply(lambda x: 'Complete' if check_complete(x) else 'Pending')
                status_counts = df_raw['📊 กลุ่มสถานะ'].value_counts().reset_index(name='จำนวน')
                if not status_counts.empty:
                    fig_pie = px.pie(status_counts, values='จำนวน', names='📊 กลุ่มสถานะ', title="สัดส่วนสถานะงานทั้งหมด", hole=0.4, color_discrete_sequence=['#10B981', '#F59E0B'])
                    st.plotly_chart(fig_pie, use_container_width=True)

    elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
        st.title("➕ ระบบกรอกข้อมูลเพิ่มประเด็นความเสี่ยง")
        st.write("กรอกแบบฟอร์มด้านล่างเพื่อส่งข้อมูลแถวใหม่เข้าสู่ไฟล์ Master ตรงๆ")
        
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            with st.form("direct_sheet_form_v4", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_date = st.date_input("📅 วันที่ (ว/ด/ป)", datetime.date.today())
                    new_topic = st.text_input("📍 ประเด็นที่พบ/ความเสี่ยง (Topic)*")
                    new_location = st.text_input("🏢 สถานที่ (Location)")
                with col2:
                    new_owner = st.text_input("👤 ผู้รับผิดชอบ (Responsible Person)*")
                    new_status = st.selectbox("🔘 สถานะแรกเริ่ม", ["⏳ Pending", "✅ Complete"])
                
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
    st.error(f"เกิดข้อผิดพลาดในการโหลดระบบ: {e}")
