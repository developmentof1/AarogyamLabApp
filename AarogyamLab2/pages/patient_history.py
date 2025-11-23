import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from num2words import num2words
import pandas as pd
import tempfile
from report_generator import generate_report_pdf_with_letterhead, generate_report_pdf_without_letterhead



if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("⚠️ Please login first from app.py")
    st.stop()
# -------------------------------
# Firebase Initialization
# -------------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("aarogyamlab-e37e4-firebase-adminsdk-fbsvc-aeb8d59129.json")
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://aarogyamlab-e37e4-default-rtdb.firebaseio.com"
    })

st.set_page_config(page_title="Patient History", layout="wide")
st.title("📜 Patient History")

patients_ref = db.reference("patients")

# -------------------------------
# Fetch all patients
# -------------------------------
patients = patients_ref.get()
if not patients:
    st.info("No patients found yet.")
    st.stop()

# Convert to list
patients_list = []
for pid, pdata in patients.items():
    pdata["id"] = pid
    patients_list.append(pdata)

# -------------------------------
# Search Filters
# -------------------------------
col1, col2 = st.columns([2, 1])
with col1:
    search_name = st.text_input("🔍 Search by Patient Name")
with col2:
    search_date = st.date_input("📅 Filter by Date (optional)", value=None)

# -------------------------------
# Filter Logic
# -------------------------------
filtered = []
for p in patients_list:
    match_name = search_name.lower() in p.get("name", "").lower() if search_name else True
    match_date = True
    if search_date:
        reg_date = p.get("registered_on", "")
        try:
            match_date = search_date.strftime("%d/%m/%Y") in reg_date
        except:
            pass
    if match_name and match_date:
        filtered.append(p)

# Sort by newest registered first
filtered = sorted(filtered, key=lambda x: x.get("registered_on", ""), reverse=True)

# -------------------------------
# Receipt Generator
# -------------------------------
def generate_receipt(patient_name, age, gender, doctor_name, date_str, tests_list):
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    filepath = tmp_file.name

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # --- Header ---
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 60, "Aarogyam Clinical Laboratory")

    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 75, "Near Niltara Hotel, Ichalkaranji, Korochi - 416109")
    c.drawCentredString(width / 2, height - 90, "Ph: 7875261778 / 7066261778")

    # --- Title ---
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 120, "RECEIPT")

    # --- Patient Info ---
    c.setFont("Helvetica", 10)
    y = height - 150
    c.drawString(60, y, f"Name : {patient_name}")
    c.drawRightString(width - 60, y, f"Date : {date_str}")

    y -= 18
    c.drawString(60, y, f"Age / Gender : {age} / {gender}")
    c.drawRightString(width - 60, y, f"Referred By : {doctor_name}")

    # --- Table Header ---
    y -= 35
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, y, "Tests Carried Out")
    c.drawRightString(width - 140, y, "Amount (Rs.)")
    c.line(50, y - 5, width - 50, y - 5)

    # --- Table Content ---
    c.setFont("Helvetica", 10)
    y -= 25
    total = 0
    for test_name, price in tests_list:
        try:
            price_val = float(price)
        except:
            price_val = 0
        c.drawString(60, y, test_name)
        c.drawRightString(420, y, f"{price_val:.2f}")
        total += price_val
        y -= 15
        if y < 100:
            c.showPage()
            y = height - 100

    # --- Total ---
    c.line(250, y - 5, 420, y - 5)
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, y, "Total Amount:")
    c.drawRightString(420, y, f"{total:.2f}")

    # --- Amount in Words ---
    y -= 35
    amount_words = num2words(total, lang='en').title()
    c.setFont("Helvetica", 10)
    c.drawString(60, y, f"Amount In Words : Rs. {amount_words} Only")

    # --- Footer ---
    y -= 50
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 60, y, "For AAROGYAM CLINICAL LABORATORY")
    y -= 40
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width / 2, y, "Thank you for visiting!")

    c.save()
    return filepath


# -------------------------------
# Table View for Patients
# -------------------------------
if filtered:
    st.subheader("📋 All Patients (Table View)")

    df_data = []
    for i, p in enumerate(filtered, start=1):
        
        status = "✅ Generated" if p.get("report_generated") else "⏳ Pending"
        df_data.append({
            "Sr No.": i,
            "Name": p.get("name", ""),
            "Age": p.get("age", ""),
            "Gender": p.get("gender", ""),
            "Doctor": p.get("doctor", ""),
            "Registered On": p.get("registered_on", ""),
            "Reported On": p.get("reported_on", "-"),
            "Total (₹)": p.get("total_bill", 0),
            "Status": status
        })

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)

    # Individual action buttons
    st.markdown("---")
    st.subheader("🧾 Actions / Generate PDF")
    for i, p in enumerate(filtered, start=1):
        with st.expander(f"{i}. {p.get('name','')}"):
            # Generate Report with Letterhead
            tests_ref = db.reference("tests")
            letterhead_path = os.path.join(os.getcwd(), "letterhead.pdf")
            pdf_path1 = generate_report_pdf_with_letterhead(
                letterhead_path,
                p,
                p.get("results", {}),
                p.get("tests", []),
                tests_ref.get() or {}
            )
            if os.path.exists(pdf_path1):
                with open(pdf_path1, "rb") as f1:
                    st.download_button(
                        label="📥 Download PDF (With Letterhead)",
                        data=f1.read(),
                        file_name=f"{p.get('name','report')}_with_letterhead.pdf",
                        mime="application/pdf",
                        uique_key=f"letterhead_{i}_{p['id']}"
                    )

            # Generate Report without Letterhead
            
            # tests_data: Dict = tests_ref.get() or {}
            pdf_path2 = generate_report_pdf_without_letterhead(
                p,
                p.get("results", {}),
                p.get("tests", []),
                tests_ref.get() or {}
            )
            if os.path.exists(pdf_path2):
                with open(pdf_path2, "rb") as f2:
                    st.download_button(
                        label="📥 Download PDF (Without Letterhead)",
                        data=f2.read(),
                        file_name=f"{p.get('name','report')}_no_letterhead.pdf",
                        mime="application/pdf",
                        unique_key=f"noletter_{i}_{p['id']}"
                    )

                # with col4:
                    # Print Receipt (optional)
                    if st.button("🧾 Print Receipt", key=f"receipt_{i}"):
                        st.info("Receipt generation logic can be added here")
    # else:
        st.info("No matching records found.")


        