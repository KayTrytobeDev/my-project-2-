import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from datetime import datetime

st.set_page_config(page_title="Risk & Corrective Tracker", layout="wide")

# ระบบจะดึงลิงก์ผ่านระบบ Secrets ของ Streamlit Cloud อัตโนมัติ
try:
    API_URL = st.secrets["SCRIPT_URL"]
except:
    API_URL = "https://script.google.com/macros/s/XXXXX/exec" 

# ดึงข้อมูลจากชีท Master
@st.cache_data(ttl=60)
def load_data_from_script():
    response = requests.get(API_URL)
    if response.status_code == 200:
        raw_data = response.json()
        headers = raw_data[0]
        rows = raw_data[1:]
        df = pd.DataFrame(rows, columns=headers)
        df.columns = df.columns.str.strip()
        return df
    return pd.DataFrame()

df = load_data_from_script()

st.sidebar.title("🚨 Navigator")
page = st.sidebar.radio("ไปยังหน้า:", ["📊 Data Visualizer", "📅 Calendar & Detail", "📝 Report New Case"])

# หน้าที่ 1: Dashboard
if page == "📊 Data Visualizer":
    st.title("📊 สรุปภาพรวมและสถิติความเสี่ยง")
    if not df.empty:
        total_cases = len(df)
        st.metric(label="📋 จำนวนเคสทั้งหมดในระบบ", value=f"{total_cases} เคส")
        st.markdown("---")
        
        # สรุปคอลัมน์ E (Status)
        st.subheader("สถานะการดำเนินงาน (Column E)")
        status_df = df['Status'].value_counts().reset_index()
        status_df.columns = ['สถานะ', 'จำนวน']
        status_df['%'] = ((status_df['จำนวน'] / total_cases) * 100).round(2)
        c1, c2 = st.columns(2)
        with c1: st.dataframe(status_df, use_container_width=True, hide_index=True)
        with c2: st.plotly_chart(px.pie(status_df, values='จำนวน', names='สถานะ', hole=0.4), use_container_width=True)
        
        st.markdown("---")
        # สรุปคอลัมน์ K (Risk Level)
        st.subheader("ระดับความเสี่ยง เรียงตามลำดับ (Column K)")
        risk_df = df['Risk Level'].value_counts().reindex(['Low', 'Medium', 'High'], fill_value=0).reset_index()
        risk_df.columns = ['ระดับความเสี่ยง', 'จำนวน']
        risk_df['%'] = ((risk_df['จำนวน'] / total_cases) * 100).round(2)
        c3, c4 = st.columns(2)
        with c3: st.dataframe(risk_df, use_container_width=True, hide_index=True)
        with c4: st.plotly_chart(px.bar(risk_df, x='ระดับความเสี่ยง', y='จำนวน', text='%', color='ระดับความเสี่ยง', color_discrete_map={'Low': '#2ca02c', 'Medium': '#ff7f0e', 'High': '#d62728'}), use_container_width=True)

# หน้าที่ 2: ปฏิทินและรายละเอียด
elif page == "📅 Calendar & Detail":
    st.title("📅 รายการเคสจำแนกตามวันเกิดเหตุ")
    if not df.empty:
        selected_date = st.selectbox("📅 เลือกวันที่จากปฏิทินข้อมูล (Column A):", sorted(df['Date'].unique(), reverse=True))
        filtered_df = df[df['Date'] == selected_date]
        
        for idx, row in filtered_df.iterrows():
            status = str(row.get('Status', ''))
            badge = "🟢" if "สำเร็จ" in status or "เรียบร้อย" in status else "🟡"
            with st.expander(f"{badge} [{row.get('Risk Level', 'Low')}] - หัวข้อ (Column B): {row.get('Topic/risk finding', '')}"):
                col_l, col_r = st.columns([2, 1])
                with col_l:
                    st.markdown(f"**📝 หัวข้อเหตุการณ์:** {row.get('Topic/risk finding', '')}")
                    st.markdown(f"**👤 ผู้รับผิดชอบ (Column D):** {row.get('Responsible Person', '-')}")
                    st.markdown(f"**🔧 แนวทางแก้ไข:** {row.get('Corrective Action', '-')}")
                    st.markdown("**📸 รูปภาพแนบ (Column I & J):**")
                    col_img1, col_img2 = st.columns(2)
                    
                    def show_img(url, title):
                        if url and str(url).startswith("http"): st.image(url, caption=title, use_container_width=True)
                        else: st.image("https://images.unsplash.com/photo-1590105577767-e21a1067899f?w=400", caption=f"{title} (รูปความปลอดภัยสากล)", use_container_width=True)
                    
                    with col_img1: show_img(row.get('Picture (before)', ''), "รูปก่อนแก้ไข")
                    with col_img2: show_img(row.get('Picture (After)', ''), "รูปหลังแก้ไข")
                with col_r:
                    if "สำเร็จ" in status or "เรียบร้อย" in status:
                        st.markdown("<div style='text-align:right;'><span style='background-color:#d4edda; color:#155724; padding:6px 15px; border-radius:15px; font-weight:bold;'>🟢 ดำเนินการสำเร็จ</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align:right;'><span style='background-color:#fff3cd; color:#856404; padding:6px 15px; border-radius:15px; font-weight:bold;'>🟡 {status}</span></div>", unsafe_allow_html=True)
                    
                    st.write("")
                    r_level = row.get('Risk Level', 'Low')
                    bg_c = "#d62728" if r_level == "High" else "#ff7f0e" if r_level == "Medium" else "#2ca02c"
                    st.markdown(f'<p style="background-color:{bg_c}; color:white; padding:8px; border-radius:5px; text-align:center; font-weight:bold;">Risk Level: {r_level}</p>', unsafe_allow_html=True)

# หน้าที่ 3: ฟอร์มส่งข้อมูล
elif page == "📝 Report New Case":
    st.title("📝 ฟอร์มกรอกข้อมูลผ่านหน้าเว็บไซต์")
    with st.form("my_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_date = st.date_input("วันที่เกิดเหตุ:", datetime.now()).strftime("%m/%d/%Y")
            f_topic = st.text_input("หัวข้อเหตุการณ์ (Topic):")
            f_location = st.text_input("สถานที่ (Location):")
            f_responsible = st.text_input("ผู้รับผิดชอบ:")
        with col_f2:
            f_status = st.selectbox("สถานะ (Status):", ["รอดำเนินการ", "กำลังดำเนินการ", "ดำเนินการเรียบร้อย"])
            f_action = st.text_area("แนวทางการแก้ไข:")
            f_risk = st.selectbox("ระดับความเสี่ยง (Risk Level):", ["Low", "Medium", "High"])
            file_before = st.file_uploader("รูปภาพก่อนแก้ไข (Before):", type=["png", "jpg", "jpeg"])
            file_after = st.file_uploader("รูปภาพหลังแก้ไข (After):", type=["png", "jpg", "jpeg"])
            
        if st.form_submit_button("🚀 บันทึกข้อมูลส่งเข้าระบบ"):
            if not f_topic: st.error("กรุณากรอกหัวข้อเหตุการณ์")
            else:
                with st.spinner("กำลังบันทึกข้อมูล..."):
                    payload = {"date": f_date, "topic": f_topic, "location": f_location, "responsible": f_responsible, "status": f_status, "action": f_action, "risk": f_risk, "imgBeforeBase64": "", "imgBeforeName": "", "imgBeforeType": "", "imgAfterBase64": "", "imgAfterName": "", "imgAfterType": ""}
                    if file_before:
                        payload["imgBeforeBase64"] = base64.b64encode(file_before.read()).decode()
                        payload["imgBeforeName"] = file_before.name
                        payload["imgBeforeType"] = file_before.type
                    if file_after:
                        payload["imgAfterBase64"] = base64.b64encode(file_after.read()).decode()
                        payload["imgAfterName"] = file_after.name
                        payload["imgAfterType"] = file_after.type
                    
                    res = requests.post(API_URL, json=payload)
                    if res.status_code == 200 and res.json().get("status") == "success":
                        st.success("🎉 บันทึกข้อมูลและอัปโหลดภาพเข้า Google Sheet เรียบร้อยแล้ว")
                        st.cache_data.clear()
                    else: st.error("เกิดข้อผิดพลาดในการส่งข้อมูล")
