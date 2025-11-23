import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import os
import json
import base64

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("⚠️ Please login first from app.py")
    st.stop()

# ===== Firebase Initialization =====
if not firebase_admin._apps:
    firebase_secret_b64 = os.environ.get("FIREBASE_ADMIN_SECRET")
    if not firebase_secret_b64:
        raise ValueError("FIREBASE_ADMIN_SECRET env variable not set")
    
    firebase_json = json.loads(base64.b64decode(firebase_secret_b64))
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://aarogyamlab-e37e4-default-rtdb.firebaseio.com/"
    })

st.set_page_config(page_title="Generate Report", layout="wide")
st.title("📄 Generate Report")

# ===== Load Patients from Firebase =====
ref = db.reference("patients")
patients = ref.get() or {}

# ===== Search Section =====
st.markdown("### 🔍 Search Patients")
col1, col2 = st.columns(2)

with col1:
    search_name = st.text_input("Search by Patient Name")
with col2:
    selected_date = st.date_input("Search by Date (Optional)", value=None)

# ===== Convert dict → list and sort newest first =====
patient_list = []
for pid, pdata in patients.items():
    pdata["id"] = pid
    reg_str = pdata.get("registered_on", "")
    try:
        dt = datetime.strptime(reg_str, "%d/%m/%Y %I:%M %p")
    except:
        try:
            dt = datetime.strptime(reg_str, "%d/%m/%Y")
        except:
            dt = datetime.min
    pdata["_parsed_date"] = dt
    patient_list.append(pdata)

patient_list.sort(key=lambda x: x["_parsed_date"], reverse=True)

# ===== Apply Filters =====
filtered_patients = []
for p in patient_list:
    name_match = search_name.lower() in p.get("name", "").lower() if search_name else True
    date_match = True
    if selected_date:
        try:
            date_match = (p["_parsed_date"].date() == selected_date)
        except:
            date_match = False
    if name_match and date_match:
        filtered_patients.append(p)

# ===== Show All Patients =====
if filtered_patients:
    st.markdown("---")
    st.subheader("🧾 All Patients (Generated + Pending)")

    for i, p in enumerate(filtered_patients, start=1):
        report_generated = p.get("report_generated", False)
        status_text = "✅ Report Generated" if report_generated else "⏳ Pending"
        status_color = "green" if report_generated else "orange"

        with st.expander(
            f"{i}. {p.get('name','')} | {p.get('gender','')} | ₹{p.get('total_bill',0)} | 📅 {p.get('registered_on','')}"
        ):
            st.markdown(
                f"**Age:** {p.get('age','')} | **Gender:** {p.get('gender','')}  \n"
                f"**Doctor:** {p.get('doctor','')}  \n"
                f"**Tests:** {', '.join(p.get('tests', []))}  \n"
                f"**Sample Collected At:** {p.get('sample_collected','')}  \n"
                f"**Registered On:** {p.get('registered_on','')}  \n"
                f"**Reported On:** {p.get('reported_on','-')}  \n"
                f"**Status:** <span style='color:{status_color};font-weight:bold'>{status_text}</span>",
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            # 🧾 Enter Test Values / Generate Report
            with col1:
                if st.button(f"✏️ Enter Test Values / Generate Report", key=f"values_{p['id']}"):
                    st.session_state["selected_patient_id"] = p["id"]
                    st.switch_page("pages/value_entry.py")

            # 📄 Download / Open Report if available
            with col2:
                pdf_path = p.get("pdf_path", "")
                if report_generated and pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📄 Download Report PDF",
                            data=f,
                            file_name=f"{p.get('name','report')}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.caption("Report not generated yet.")
else:
    st.info("No matching records found.")
