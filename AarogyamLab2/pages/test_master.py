import streamlit as st
import firebase_admin
from firebase_admin import credentials, db

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("⚠️ Please login first from app.py")
    st.stop()
# ========== Firebase Initialization ==========
if not firebase_admin._apps:
    cred = credentials.Certificate("aarogyamlab-e37e4-firebase-adminsdk-fbsvc-aeb8d59129.json")
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://aarogyamlab-e37e4-default-rtdb.firebaseio.com"
    })

st.set_page_config(page_title="Test Master", layout="wide")
st.title("🧪 Test Master")
st.caption("Add, Edit, and Delete Laboratory Tests with Sub-tests and Parameters")

# ========== Firebase Reference ==========
ref = db.reference("tests")

# ========== Session State ==========
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "editing_test" not in st.session_state:
    st.session_state.editing_test = None
if "subtests" not in st.session_state:
    st.session_state.subtests = []
if "price" not in st.session_state:
    st.session_state.price = 0

# ========== Load Tests ==========
all_tests = ref.get() or {}

# ======================== TEST FORM ========================
if st.session_state.edit_mode:
    st.subheader(f"✏️ Editing Test — {st.session_state.editing_test}")
    main_test = st.text_input("Main Test Name", st.session_state.editing_test)
    price = st.number_input("Test Price (₹)", min_value=0, value=int(st.session_state.price))
else:
    st.subheader("➕ Add New Test")
    main_test = st.text_input("Main Test Name (उदा. CBC, LFT, Blood Sugar)")
    price = st.number_input("Test Price (₹)", min_value=0, step=10)

st.markdown("---")
st.subheader("🔹 Sub-Tests")

# Add new Sub-Test
if st.button("+ Add Sub-Test"):
    st.session_state.subtests.append({"name": "", "unit": "", "range": "", "sub_params": []})

updated_subtests = []

# --- Sub-Test Editor ---
for i, sub in enumerate(st.session_state.subtests):
    with st.expander(f"Sub-Test {i+1}: {sub['name'] or 'Unnamed'}", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 0.5])
        with c1:
            name = st.text_input("Sub-Test Name", sub["name"], key=f"name_{i}")
        with c2:
            unit = st.text_input("Unit", sub["unit"], key=f"unit_{i}")
        with c3:
            normal_range = st.text_input("Normal Range", sub["range"], key=f"range_{i}")
        with c4:
            if st.button("❌ Remove", key=f"remove_sub_{i}"):
                st.session_state.subtests.pop(i)
                st.rerun()

        # Sub-Parameters Section
        st.markdown("**⚙️ Sub-Parameters:**")
        if f"params_{i}" not in st.session_state:
            st.session_state[f"params_{i}"] = sub.get("sub_params", [])

        if st.button(f"+ Add Parameter {i+1}", key=f"add_param_{i}"):
            st.session_state[f"params_{i}"].append({
                "name": "",
                "unit": "",
                "range": "",
                "options": ""
            })

        updated_params = []
        for j, p in enumerate(st.session_state[f"params_{i}"]):
            pcol1, pcol2, pcol3, pcol4 = st.columns(4)
            with pcol1:
                pname = st.text_input("Name", p["name"], key=f"pname_{i}_{j}")
            with pcol2:
                punit = st.text_input("Unit", p["unit"], key=f"punit_{i}_{j}")
            with pcol3:
                prange = st.text_input("Range", p["range"], key=f"prange_{i}_{j}")
            with pcol4:
                popts = st.text_input("Options", p["options"], key=f"popt_{i}_{j}")
            updated_params.append({
                "name": pname,
                "unit": punit,
                "range": prange,
                "options": popts
            })

        updated_subtests.append({
            "name": name,
            "unit": unit,
            "range": normal_range,
            "sub_params": updated_params
        })

st.session_state.subtests = updated_subtests

st.markdown("---")

# ======================== SAVE BUTTON ========================
if st.button("💾 Save Test"):
    if not main_test.strip():
        st.warning("Please enter a main test name!")
    else:
        data = {
            "price": price,
            "subtests": st.session_state.subtests
        }
        ref.child(main_test).set(data)
        st.success(f"✅ '{main_test}' saved successfully!")

        # ===== Clear form after save =====
        for key in list(st.session_state.keys()):
            if key.startswith("params_") or key.startswith("name_") or key.startswith("unit_") or key.startswith("range_"):
                del st.session_state[key]

        st.session_state.subtests = []
        st.session_state.edit_mode = False
        st.session_state.editing_test = None
        st.session_state.price = 0

        st.rerun()


# ======================== SHOW ALL TESTS ========================
st.markdown("---")
st.subheader("📊 Saved Tests (Click Edit or Delete)")

all_tests = ref.get()
if all_tests:
    for tname, tdata in all_tests.items():
        with st.container(border=True):
            st.markdown(f"### 🧾 {tname} — ₹{tdata.get('price', 0)}")

            # Sub-tests view
            for s in tdata.get("subtests", []):
                st.write(f"- **{s['name']}** | {s['unit']} | {s['range']}")
                if s.get("sub_params"):
                    with st.expander("View Sub-Parameters"):
                        for p in s["sub_params"]:
                            opt_text = f" | Options: {p['options']}" if p.get("options") else ""
                            st.write(f" - {p['name']} ({p['unit']}) — {p['range']}{opt_text}")

            # Edit/Delete Buttons
            col1, col2 = st.columns([0.1, 0.1])
            with col1:
                if st.button(f"✏️ Edit {tname}", key=f"edit_{tname}"):
                    st.session_state.edit_mode = True
                    st.session_state.editing_test = tname
                    st.session_state.subtests = tdata["subtests"]
                    st.session_state.price = tdata["price"]
                    st.rerun()
            with col2:
                if st.button(f"🗑️ Delete {tname}", key=f"delete_{tname}"):
                    ref.child(tname).delete()
                    st.success(f"🗑️ '{tname}' deleted successfully!")
                    st.rerun()
else:
    st.info("No tests found yet.")
