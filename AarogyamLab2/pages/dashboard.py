import streamlit as st

# -------------------------------
# Check login status
# -------------------------------
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("⚠️ Please login first from app.py")
    st.stop()

st.set_page_config(page_title="Aarogyam Lab Dashboard", page_icon="🏥", layout="wide")
st.title("🏥 Aarogyam Lab Dashboard")
st.write(f"Welcome, **{st.session_state['username']}** 👋")

# -------------------------------
# Sidebar Navigation
# -------------------------------
st.sidebar.title("📋 Navigation")
menu = st.sidebar.radio("Go to:", [
   "🏠 Dashboard",
   "🚪 Logout"
])

if menu == "🏠 Dashboard":
    st.subheader("📊 Overall Statistics")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total Patients", "0")
    with col2: st.metric("Total Tests", "0")
    with col3: st.metric("Today's Income", "0 ₹")

elif menu == "🚪 Logout":
    st.session_state['logged_in'] = False
    st.success("✅ Logged out successfully!")
    st.stop() # This reloads app.py
