import streamlit as st
import firebase_admin
from firebase_admin import credentials, db

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("⚠️ Please login first from app.py")
    st.stop()
    
# ===== Initialize Firebase =====
if not firebase_admin._apps:
    cred = credentials.Certificate("aarogyamlab-e37e4-firebase-adminsdk-fbsvc-aeb8d59129.json")
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://aarogyamlab-e37e4-default-rtdb.firebaseio.com"
    })

st.set_page_config(page_title="Doctor Master", layout="wide")
st.title("👨‍⚕️ Doctor Master")

# ===== Firebase reference =====
ref = db.reference("doctors")

# ===== Session state =====
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None
if "form_key" not in st.session_state:
    st.session_state.form_key = 0  

# ===== Input Fields =====
st.subheader("➕ Add / ✏️ Edit Doctor")

form_key = st.session_state.form_key  # dynamic key
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Doctor Name", key=f"name_{form_key}")
with col2:
    qualification = st.text_input("Qualification", key=f"qual_{form_key}")

# ===== Save Button =====
if st.button("💾 Save Doctor"):
    if not name.strip() or not qualification.strip():
        st.warning("Please enter both name and qualification.")
    else:
        doctor_data = {"name": name.strip(), "qualification": qualification.strip()}

        if st.session_state.edit_mode and st.session_state.edit_id:
            # Update existing
            ref.child(st.session_state.edit_id).update(doctor_data)
            st.success(f"✅ Doctor '{name}' updated successfully!")
        else:
            # Add new
            ref.push(doctor_data)
            st.success(f"✅ Doctor '{name}' added successfully!")

        # 🔁 Reset form (important)
        st.session_state.edit_mode = False
        st.session_state.edit_id = None
        st.session_state.form_key += 1  

        st.rerun()

# ===== Display All Doctors =====
st.markdown("---")
st.subheader("🩺 Saved Doctors")

doctors_data = ref.get()
if doctors_data:
    for doc_id, doc in doctors_data.items():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.write(f"**{doc['name']}** ({doc['qualification']})")
        with c2:
            if st.button("✏️ Edit", key=f"edit_{doc_id}"):
                st.session_state.edit_mode = True
                st.session_state.edit_id = doc_id
                st.session_state.form_key += 1  
                st.session_state[f"name_{st.session_state.form_key}"] = doc["name"]
                st.session_state[f"qual_{st.session_state.form_key}"] = doc["qualification"]
                st.rerun()
        with c3:
            if st.button("🗑️ Delete", key=f"del_{doc_id}"):
                ref.child(doc_id).delete()
                st.warning(f"🗑️ Doctor '{doc['name']}' deleted.")
                st.rerun()
else:
    st.info("No doctors found yet.")
