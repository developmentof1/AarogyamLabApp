import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import pandas as pd

# ===== Login Check =====
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("⚠️ Please login first from app.py")
    st.stop()
    
# ===== Initialize Firebase =====
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("aarogyamlab-e37e4-firebase-adminsdk-fbsvc-aeb8d59129.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://aarogyamlab-e37e4-default-rtdb.firebaseio.com/"
        })
    except Exception as e:
        st.error(f"⚠️ Firebase initialization failed: {e}")
        st.stop()

st.set_page_config(page_title="Patient Entry", layout="wide")
st.title("🧍‍♂️ Patient Entry / Edit Form")

# ===== Load existing patients =====
try:
    patients_ref = db.reference("patients")
    patients = patients_ref.get() or {}
except Exception as e:
    st.error(f"Unable to load patients from Firebase: {e}")
    patients = {}

# ===== Dropdown साठी display string तयार करा =====
patient_options = ["➕ New Patient"]
patient_map = {}
for pid, pdata in patients.items():
    name = pdata.get("name", "Unknown")
    age = pdata.get("age", "")
    reg_date = pdata.get("registered_on", "")
    display_str = f"{name} | {age} | {reg_date}"
    patient_options.append(display_str)
    patient_map[display_str] = pid

# ===== Dropdown =====
selected_patient_display = st.selectbox("Select Existing Patient (Edit)", patient_options)

selected_patient = None
if selected_patient_display != "➕ New Patient":
    pid = patient_map[selected_patient_display]
    selected_patient = patients.get(pid, {})
    selected_patient["id"] = pid

# ===== Registration Date & Time =====
st.markdown("### 🕒 Registration Date & Time")
current_dt = datetime.now().strftime("%d/%m/%Y %I:%M %p")
registration_dt = st.text_input(
    "Enter / Edit Registration Date & Time",
    value=selected_patient.get("registered_on", current_dt) if selected_patient else current_dt,
    help="Change date/time if needed (format: DD/MM/YYYY HH:MM AM/PM)"
)

# ===== Load Doctors =====
try:
    doc_ref = db.reference("doctors")
    doctors = doc_ref.get() or {}
    doctor_list = [f"{v['name']} ({v['qualification']})" for v in doctors.values()] if isinstance(doctors, dict) else []
except Exception as e:
    st.error(f"Unable to load doctors from Firebase: {e}")
    doctor_list = []

# ===== Load Tests =====
try:
    test_ref = db.reference("tests")
    tests = test_ref.get() or {}
    test_names = list(tests.keys())
except Exception as e:
    st.error(f"Unable to load tests from Firebase: {e}")
    tests = {}
    test_names = []
# ===== Patient Info =====
st.subheader("👤 Patient Information")

col1, col2 = st.columns(2)
with col1:
    titles = ["Mr.", "Mrs.", "Miss", "Master", "Smt."]
    try:
        title_index = titles.index(selected_patient.get("name","Mr.").split()[0])
    except:
        title_index = 0
    title = st.selectbox("Title", titles, index=title_index)
    
    try:
        name_val = " ".join(selected_patient.get("name","").split()[1:])
    except:
        name_val = ""
    name = st.text_input("Patient Name", value=name_val)
    
    gender_index = 0 if not selected_patient else (0 if selected_patient.get("gender")=="Male" else 1)
    gender = st.selectbox("Gender", ["Male", "Female"], index=gender_index)
    
    phone = st.text_input("Phone (Optional)", value=selected_patient.get("phone","") if selected_patient else "")

with col2:
    try:
        age_parts = selected_patient.get("age","").split()
        age_val = age_parts[0] if len(age_parts)>0 else ""
        age_type_val = age_parts[1] if len(age_parts)>1 else "Years"
    except:
        age_val, age_type_val = "", "Years"
    age = st.text_input("Age", value=age_val)
    age_type = st.selectbox("Age Type", ["Years", "Months", "Days"], index=["Years","Months","Days"].index(age_type_val) if age_type_val in ["Years","Months","Days"] else 0)
    
    sample_collected = st.selectbox("Sample Collected At", ["Inside Lab", "Outside Lab"], index=0 if not selected_patient else (0 if selected_patient.get("sample_collected","Inside Lab")=="Inside Lab" else 1))
    
    try:
        doctor_index = (["-- Select --"] + doctor_list).index(selected_patient.get("doctor","-- Select --")) if selected_patient else 0
    except:
        doctor_index = 0
    doctor = st.selectbox("Select Doctor", ["-- Select --"] + doctor_list, index=doctor_index)
    manual_doctor = st.text_input("Doctor Name (if not listed)", value="" if selected_patient is None else ("" if selected_patient.get("doctor") in doctor_list else selected_patient.get("doctor","")))

# ===== Test Selection =====
st.subheader("🧪 Test Selection")
selected_tests = st.multiselect(
    "Select Tests", 
    test_names,
    default=selected_patient.get("tests", []) if selected_patient else []
)

test_data = []
total_bill = 0
for test in selected_tests:
    price = int(tests.get(test, {}).get("price", 0))
    test_data.append({"Test Name": test, "Price (₹)": price})
    total_bill += price

if selected_tests:
    st.write("### Selected Tests & Prices")
    st.table(pd.DataFrame(test_data))
    st.markdown(f"### 💰 Total Bill: ₹{total_bill}")
else:
    st.info("Select one or more tests to see their price.")

# ===== Save / Update Function =====
def save_or_update_patient(is_update=False):
    if not name.strip():
        st.warning("Please enter patient name.")
        return
    if not selected_tests:
        st.warning("Please select at least one test.")
        return

    final_doctor = doctor if doctor != "-- Select --" else manual_doctor
    patient_data = {
        "name": f"{title} {name}",
        "age": f"{age} {age_type}",
        "gender": gender,
        "phone": phone,
        "doctor": final_doctor,
        "tests": selected_tests,
        "total_bill": total_bill,
        "sample_collected": sample_collected,
        "registered_on": registration_dt,
        "report_generated": False,
        "reported_on": "",
        "pdf_path": "",
    }

    try:
        if is_update:
            patients_ref.child(selected_patient["id"]).update(patient_data)
            st.success(f"✅ Patient '{name}' updated successfully!")
        else:
            unique_id = f"{name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            patient_data["id"] = unique_id
            patients_ref.child(unique_id).set(patient_data)
            st.success(f"✅ Patient '{name}' saved successfully!")
    except Exception as e:
        st.error(f"⚠️ Failed to save/update patient: {e}")

# ===== Buttons =====
if selected_patient:
    if st.button("💾 Update Patient Entry"):
        save_or_update_patient(is_update=True)
else:
    if st.button("💾 Save Patient Entry"):
        save_or_update_patient(is_update=False)

# ===== View Saved Patients =====
st.markdown("---")
st.subheader("📋 Today's Patients (Newest First)")
if patients:
    today_str = datetime.now().strftime("%d/%m/%Y")
    today_patients = {pid:pdata for pid,pdata in patients.items() if today_str in pdata.get("registered_on","")}
    if today_patients:
        sorted_patients = sorted(today_patients.items(), key=lambda x:x[1].get("registered_on",""), reverse=True)
        for pid, pdata in sorted_patients:
            bill = pdata.get("total_bill",0)
            with st.expander(f"🧾 {pdata.get('name','')} | {pdata.get('gender','')} | ₹{bill}"):
                st.write(f"**Age:** {pdata.get('age','')}")
                st.write(f"**Doctor:** {pdata.get('doctor','')}")
                st.write(f"**Tests:** {', '.join(pdata.get('tests',[]))}")
                st.write(f"**Registered On:** {pdata.get('registered_on','')}")
                st.write(f"**Sample Collected At:** {pdata.get('sample_collected','')}")
    else:
        st.info("📅 No patients registered today.")
else:
    st.info("No patients found yet.")
