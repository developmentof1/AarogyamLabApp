import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import requests
import os
import json
import base64
from report_generator import (
    generate_report_pdf_with_letterhead,
    generate_report_pdf_without_letterhead, 
    merge_with_letterhead
)
import re
import urllib.parse

def make_key_safe(key: str) -> str:
    """Firebase key मध्ये invalid characters replace करते"""
    import re
    return re.sub(r'[.$#\[\]/\(\)\s]', '_', key)


# ========== Firebase Init ==========
if not firebase_admin._apps:
    firebase_secret_b64 = os.environ.get("FIREBASE_ADMIN_SECRET")
    if not firebase_secret_b64:
        raise ValueError("FIREBASE_ADMIN_SECRET env variable not set")
    
    firebase_json = json.loads(base64.b64decode(firebase_secret_b64))
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://aarogyamlab-e37e4-default-rtdb.firebaseio.com/"
    })

st.set_page_config(page_title="Value Entry", layout="wide")
st.title("🧪 Enter Test Values")

# ✅ Get patient ID from session
if "selected_patient_id" not in st.session_state:
    st.warning("⚠️ Please open this page from 'Generate Report'.")
    st.stop()

patient_id = st.session_state["selected_patient_id"]

# ---------------------------
# Firebase References
# ---------------------------
patients_ref = db.reference("patients")
tests_ref = db.reference("tests")

patient_data = patients_ref.child(patient_id).get()
if not patient_data:
    st.error("❌ Patient not found!")
    st.stop()

test_data = tests_ref.get() or {}
test_data = dict(sorted(test_data.items(), key=lambda x: x[0]))  # keeps consistent order

# ---------------------------
# Firebase-safe key helper
# ---------------------------
def make_key_safe(name: str):
    """Firebase-safe key (replace invalid chars)"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

def get_saved_value(saved_dict, test, sub, param=None):
    """Fetch old value using both original & safe keys"""
    safe_sub = make_key_safe(sub)
    if param:
        safe_param = make_key_safe(param)
        key1 = f"{test}::{sub}::{param}"
        key2 = f"{test}::{safe_sub}::{safe_param}"
    else:
        key1 = f"{test}::{sub}"
        key2 = f"{test}::{safe_sub}"

    if key1 in saved_dict:
        return saved_dict[key1].get("value", "")
    elif key2 in saved_dict:
        return saved_dict[key2].get("value", "")
    else:
        return ""


# ---------------------------
# Header info
# ---------------------------
st.markdown(f"### 👤 Patient: **{patient_data['name']}**")
st.write(f"🧾 Doctor: {patient_data.get('doctor','')}")
st.write(f"📅 Registered On: {patient_data.get('registered_on','')}")

# ---------------------------
# Load existing saved values
# ---------------------------
saved_results = patient_data.get("results", {})
entered_values = {}

# ---------------------------
# Table-Style Value Entry
# ---------------------------
for test_name in patient_data.get("tests", []):
    test_info = test_data.get(test_name)
    if not test_info:
        continue

    st.markdown("### 🧬 Select Category for Test")

    categories = [
        "HEMATOLOGY", "BIOCHEMISTRY", "MICROBIOLOGY",
        "CLINICAL PATHOLOGY", "SEROLOGY", "URINE EXAMINITION", "EXAMINATION OF BLOOD"
    ]

    prev_cat = saved_results.get(f"category_{test_name}", {}).get("value", "") if saved_results else ""

    selected_category = st.selectbox(
        f"Category for {test_name}",
        options=["-- Select Category --"] + categories,
        index=(["-- Select Category --"] + categories).index(prev_cat) if prev_cat in categories else 0,
        key=f"cat_{test_name}"
    )

    entered_values[f"category_{test_name}"] = {"value": "" if selected_category == "-- Select Category --" else selected_category}

    st.markdown("---")
    st.markdown(f"## 🧫 {test_name}  (₹{test_info.get('price', 0)})")

    subtests = test_info.get("subtests", [])
    if not subtests:
        st.info("No sub-tests defined for this test.")
        continue

    # Table header
    col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
    with col1: st.markdown("**Sub-Test / Parameter**")
    with col2: st.markdown("**Value**")
    with col3: st.markdown("**Unit**")
    with col4: st.markdown("**Normal Range**")

    # --- Loop through subtests ---
    for s in subtests:
        sub_name = s["name"]
        safe_sub_name = make_key_safe(sub_name)
        sub_unit = s.get("unit", "")
        sub_range = s.get("range", "")

        c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
        with c1:
            st.markdown(f"🧩 **{sub_name}**")
        # key_name = f"{test_name}::{safe_sub_name}"
        

        with c2:
            prev_val = get_saved_value(saved_results, test_name, sub_name)
            val = st.text_input(
                label="",
                key=f"val_{test_name}_{safe_sub_name}",
                placeholder="Enter value",
                value=prev_val,
                label_visibility="collapsed"
            )

        with c3:
            st.markdown(f"<p style='margin-top:4px'>{sub_unit}</p>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<p style='margin-top:4px'>{sub_range}</p>", unsafe_allow_html=True)

        safe_sub = make_key_safe(sub_name)
        key_name = f"{test_name}::{safe_sub}".strip()
        entered_values[key_name] = {
            "value": val,
            "unit": sub_unit,
            "range": sub_range,
            "original_name": sub_name  # for report display
        }
        

        # --- Sub-Parameters (if any) ---
        for param in s.get("sub_params", []):
            pname = param["name"]
            safe_pname = make_key_safe(pname)
            punit = param.get("unit", "")
            prange = param.get("range", "")
            popts = param.get("options", "")
            safe_p = make_key_safe(pname)
            # prev_val = get_saved_value(saved_results, test_name, sub_name)

            if isinstance(popts, str) and popts.strip():
                popts = [opt.strip() for opt in popts.split(",")]
            else:
                popts = []

            c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
            with c1:
                st.markdown(f"↳ **{pname}**")

            key_name = f"{test_name}::{safe_sub_name}::{safe_pname}"
            prev_val = get_saved_value(saved_results, test_name, sub_name, pname)

            with c2:
                if popts:
                    options_with_manual = ["-- Select or Type --"] + popts
                    selected_opt = st.selectbox(
                        label="",
                        options=options_with_manual,
                        index=options_with_manual.index(prev_val) if prev_val in options_with_manual else 0,
                        key=f"opt_{test_name}_{safe_sub_name}_{safe_pname}",
                        label_visibility="collapsed",
                    )
                    if selected_opt == "-- Select or Type --":
                        val = st.text_input(
                            label="",
                            key=f"val_{test_name}_{safe_sub_name}_{safe_pname}",
                            placeholder="Type custom value here...",
                            value=prev_val if prev_val not in popts else "",
                            label_visibility="collapsed",
                        )
                    else:
                        val = selected_opt
                else:
                    val = st.text_input(
                        label="",
                        key=f"val_{test_name}_{safe_sub_name}_{safe_pname}",
                        placeholder="Enter value",
                        value=prev_val,
                        label_visibility="collapsed",
                    )

            with c3:
                st.markdown(f"<p style='margin-top:4px'>{punit}</p>", unsafe_allow_html=True)
            with c4:
                st.markdown(f"<p style='margin-top:4px'>{prange}</p>", unsafe_allow_html=True)

            safe_sub = make_key_safe(sub_name)
            safe_p = make_key_safe(pname)
            key_name = f"{test_name}::{safe_sub}::{safe_p}".strip()
            entered_values[key_name] = {
                "value": val,
                "unit": punit,
                "range": prange,
                "original_name": pname
            }
            

    # --- Description / Remarks ---
    st.markdown("**📝 Description / Remarks:**")
    prev_desc = saved_results.get(f"{test_name}::description", "")
    description = st.text_area(
        f"desc_{test_name}",
        placeholder=f"Write any notes or observations for {test_name}...",
        value=prev_desc,
        key=f"desc_{test_name}"
    )
    entered_values[f"{test_name}::description"] = description
    st.divider()


# ✅ Clean invalid Firebase data
def clean_for_firebase(data):
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if any(x in k for x in [".", "$", "#", "[", "]", "/"]):
                continue
            cleaned = clean_for_firebase(v)
            if cleaned in [None, "", [], {}, set()]:
                continue
            new_dict[k] = cleaned
        return new_dict
    elif isinstance(data, list):
        return [clean_for_firebase(x) for x in data if x not in [None, "", [], {}, set()]]
    elif isinstance(data, (set, type, bytes)):
        return None
    else:
        return data

# ---------------------------
# Save Results Button
# ---------------------------
show_generate = patient_data.get("results") is not None
current_datetime = datetime.now()
reported_on_str = current_datetime.strftime("%d/%m/%Y %I:%M %p")

if st.button("💾 Save Results"):
    if not entered_values:
        st.warning("⚠️ No values entered!")
    else:
        all_results = patient_data.get("results", {})
        all_results.update(entered_values)
        patient_data["results"] = all_results
        patient_data["report_generated"] = False
        patient_data["reported_on"] = reported_on_str

        try:
            safe_data = clean_for_firebase(patient_data)
            patients_ref.child(patient_id).update(safe_data)
            st.success(f"✅ Results saved successfully for {patient_data['name']}!")
            st.balloons()
            show_generate = True
        except Exception as e:
            st.error(f"⚠️ Firebase update failed: {e}")
        print("\n\n=========== DEBUG RESULTS ===========")
        for k, v in entered_values.items():
            print(k, "=>", v)
        print("=========== END DEBUG ===========\n\n")

# ---------------- PDF Generation ----------------
if show_generate or patient_data.get("results"):
    st.markdown("---")
    st.subheader("📄 Generate Report PDF")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧾 Generate With Letterhead"):
            letterhead_path = os.path.join(os.getcwd(), "letterhead(1).pdf")  # relative path
            final_report, qr_img_path = generate_report_pdf_with_letterhead(letterhead_path, patient_data, patient_data["results"], patient_data.get("tests", []), test_data)
            st.success("✅ Report generated with letterhead!")

            # WhatsApp Link
            phone = patient_data.get("phone","").replace("+","").replace(" ","")
            if phone.startswith("0"): phone = phone[1:]
            if phone:
                pdf_link = final_report.replace("\\","/")
                message = f"Hello {patient_data['name']},\nYour report is ready! Download: {pdf_link}"
                encoded_msg = urllib.parse.quote(message)
                whatsapp_url = f"https://api.whatsapp.com/send?phone={phone}&text={encoded_msg}"
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="padding:8px 16px;background:#25D366;color:white;border:none;border-radius:5px;font-size:14px;">📤 Send via WhatsApp</button></a>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ No valid phone number found.")

    with col2:
        if st.button("📄 Generate Without Letterhead"):
            temp_report_path, qr_path = generate_report_pdf_without_letterhead(patient_data, patient_data["results"], patient_data.get("tests", []), test_data)
            st.success("✅ PDF generated without letterhead!")
            if os.path.exists(temp_report_path):
                with open(temp_report_path, "rb") as f:
                    st.download_button(
                        label="Download PDF",
                        data=f,
                        file_name=os.path.basename(temp_report_path),
                        mime="application/pdf"
                    )
            
                    
# ---------------------------
# Navigation
# ---------------------------
if st.button("⬅ Back to Generate Report"):
    st.switch_page("pages/generate_report.py")
