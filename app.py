# คัดลอกเฉพาะพาร์ทเมนูบันทึกข้อมูลในไฟล์ app.py ไปอัปเดตแทนที่ตรงเมนูที่ 3 ได้เลยครับ
    elif menu == "➕ บันทึกข้อมูลเพิ่มเข้าตารางหลัก":
        st.title("➕ บันทึกข้อมูลประเด็นความเสี่ยงลง Google Sheet")
        
        # 🔗 ใส่ลิงก์เว็บแอปตัวใหม่ที่คุณทำการ Deploy ล่าสุดจากข้อ 1 ด้านบน
        API_URL = "https://script.google.com/macros/s/AKfycbyb17lC8nve1YstfR-z6V2mD5q57_gRlygC-PzB9bI3z1fWp5tRE_X8k0_o_SgU66G3/exec"
        
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
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
                            # คำนวณแปลงปี ค.ศ. ให้เป็น พ.ศ. (+543) เพื่อให้ตรงกับโครงสร้างวันที่เดิมในตารางโรงพยาบาลของคุณ
                            th_year = new_date.year + 543
                            str_date_combined = f"{new_date.month}/{new_date.day}/{th_year}"
                            
                            payload = {
                                "formatted_date": str_date_combined, // รวมวันเดือนปีไว้ส่งช่องเดียว
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
            st.markdown('</div>', unsafe_allow_html=True)
