import streamlit as st
import plotly.express as px
# เรียกใช้ฟังก์ชันจากไฟล์ utils.py
from utils import load_data, check_complete

# --- 1. ตั้งค่าหน้าจอและสไตล์ (Theme) ---
st.set_page_config(page_title="Corrective Action Tracker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSelectbox label { font-size: 18px !important; font-weight: bold; color: #1E3A8A; }
    .card {
        background-color: white;
        padding: 22px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border-left: 8px solid #3B82F6;
    }
    .complete-card { border-left: 8px solid #10B981 !important; }
    .status-badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    .status-complete { background-color: #D1FAE5; color: #065F46; }
    .status-pending { background-color: #FEF3C7; color: #92400E; }
    </style>
    """, unsafe_allow_html=True)

try:
    df_raw = load_data()
    
    # --- 2. เมนูสลับหน้าจอ (Navigation) ---
    st.sidebar.title("📌 เมนูหลัก")
    menu = st.sidebar.radio("เลือกโหมดการแสดงผล", ["📋 หน้าหลัก (รายเคส)", "📊 สรุปภาพรวม (Dashboard)"])

    if menu == "📋 หน้าหลัก (รายเคส)":
        st.title("📋 ระบบติดตามประเด็นความเสี่ยงและการแก้ไข")
        
        # --- 3. ส่วนของ Filters (อยู่กึ่งกลางหน้าหลัก) ---
        st.markdown("### 🔍 ค้นหาและคัดกรองข้อมูล")
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            dates = ["ทั้งหมด"] + sorted(df_raw['ว/ด/ป'].dropna().unique().tolist())
            sel_date = st.selectbox("📅 เลือก ว/ด/ป", dates)
            
        with f_col2:
            owners = ["ทั้งหมด"] + sorted(df_raw['Responsible Person'].dropna().unique().tolist())
            sel_owner = st.selectbox("👤 ผู้รับผิดชอบ", owners)
            
        with f_col3:
            statuses = ["ทั้งหมด"] + sorted(df_raw['Status'].dropna().unique().tolist())
            sel_status = st.selectbox("🔘 สถานะงาน", statuses)

        # กรองข้อมูลตามที่เลือก
        df = df_raw.copy()
        if sel_date != "ทั้งหมด": df = df[df['ว/ด/ป'] == sel_date]
        if sel_owner != "ทั้งหมด": df = df[df['Responsible Person'] == sel_owner]
        if sel_status != "ทั้งหมด": df = df[df['Status'] == sel_status]

        # --- 4. แสดงผลในรูปแบบ Cards ---
        st.divider()
        if df.empty:
            st.warning("ไม่พบข้อมูลที่ตรงตามเงื่อนไขที่เลือก")
        else:
            for _, row in df.iterrows():
                is_complete = check_complete(row.get('Status', ''))
                
                card_class = "card complete-card" if is_complete else "card"
                status_html = '<span class="status-badge status-complete">✅ เรียบร้อย</span>' if is_complete else '<span class="status-badge status-pending">⏳ กำลังดำเนินการ</span>'
                
                with st.container():
                    st.markdown(f"""
                        <div class="{card_class}">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin:0; color:#1E3A8A;">📍 {row.get('Topic/risk finding', 'N/A')}</h3>
                                {status_html}
                            </div>
                            <p style="font-size:16px; margin-top:8px; color: #4B5563;">
                                <b>สถานที่:</b> {row.get('Location', 'N/A')} | 
                                <b>ผู้รับผิดชอบ:</b> {row.get('Responsible Person', 'N/A')}
                            </p>
                            <p style="font-size:16px;"><b>แนวทางการแก้ไข:</b> {row.get('Corrective Action', 'ไม่มีข้อมูล')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # รูปภาพเปรียบเทียบ Before / After
                    img_col1, img_col2 = st.columns(2)
                    with img_col1:
                        st.caption("📸 ภาพก่อนแก้ไข (Before)")
                        if pd.notna(row['Picture (before)']):
                            st.image(row['Picture (before)'], use_container_width=True)
                    with img_col2:
                        st.caption("✅ ภาพหลังแก้ไข (After)")
                        if is_complete and pd.notna(row['Picture (After)']):
                            st.image(row['Picture (After)'], use_container_width=True)
                        elif not is_complete:
                            st.info("💡 อยู่ระหว่างรอดำเนินการแก้ไข (ยังไม่มีภาพ After)")
                    st.markdown("<br>", unsafe_allow_html=True)

    else:
        # --- 5. หน้าสรุปภาพรวม (Dashboard) ---
        st.title("📊 สรุปภาพรวมโครงการ (Dashboard)")
        
        # คำนวณ Metric หลัก
        total = len(df_raw)
        done = df_raw['Status'].apply(check_complete).sum()
        pending = total - done
        percent = (done / total) * 100 if total > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("งานทั้งหมด", f"{total} เคส")
        m2.metric("เสร็จสิ้นแล้ว", f"{done} เคส", delta=f"{percent:.1f}%")
        m3.metric("คงค้างอยู่", f"{pending} เคส", delta_color="inverse")
        m4.metric("จำนวนผู้รับผิดชอบ", df_raw['Responsible Person'].nunique())
        
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            # กราฟแท่งแยกตามผู้รับผิดชอบ
            owner_counts = df_raw.groupby('Responsible Person').size().reset_index(name='จำนวนงาน')
            fig_owner = px.bar(owner_counts, x='Responsible Person', y='จำนวนงาน', 
                               title="ปริมาณงานแยกตามผู้รับผิดชอบ", color_discrete_sequence=['#3B82F6'])
            st.plotly_chart(fig_owner, use_container_width=True)
            
        with c2:
            # กราฟวงกลมแสดงสัดส่วนสถานะ
            # แปลงสถานะให้อ่านง่ายสำหรับกราฟ
            df_raw['📊 กลุ่มสถานะ'] = df_raw['Status'].apply(lambda x: 'Complete' if check_complete(x) else 'Pending')
            status_counts = df_raw['📊 กลุ่มสถานะ'].value_counts().reset_index()
            fig_pie = px.pie(status_counts, values='count', names='📊 กลุ่มสถานะ', 
                             title="สัดส่วนสถานะงานทั้งหมด", hole=0.4,
                             color_discrete_sequence=['#10B981', '#F59E0B'])
            st.plotly_chart(fig_pie, use_container_width=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดระบบ: {e}")
