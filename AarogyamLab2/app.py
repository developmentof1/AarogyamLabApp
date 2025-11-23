import streamlit as st
import sqlite3
# from dotenv import load_dotenv
import os

# ------------------ Load env variables ------------------
# load_dotenv()
# firebase_secret_b64 = os.environ.get("FIREBASE_ADMIN_SECRET")
# if not firebase_secret_b64:
#     raise ValueError("FIREBASE_ADMIN_SECRET env variable not set")

# ------------------ Database ------------------
DB_PATH = "aarogyam_lab.db"

def create_usertable():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT)')
    conn.commit()
    conn.close()

def add_userdata(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO users(username,password) VALUES (?,?)', (username, password))
    conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    data = c.fetchall()
    conn.close()
    return data

create_usertable()

# ------------------ Streamlit Config ------------------
st.set_page_config(page_title="Aarogyam Lab", layout="wide")

# ------------------ Login State ------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# ------------------ Login / Signup ------------------
if not st.session_state['logged_in']:
    st.title("🏥 Aarogyam Lab - Login / Sign Up")
    menu = ["Login", "Sign Up"]
    choice = st.selectbox("Menu", menu)

    if choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            result = login_user(username, password)
            if result:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.success(f"✅ Welcome, {username} 👋")
                st.stop() 
            else:
                st.error("❌ Invalid Username or Password")
    else:
        new_user = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Sign Up"):
            if new_user and new_password:
                add_userdata(new_user, new_password)
                st.success("✅ Account created successfully!")
                st.info("➡️ Go to Login menu to log in.")
            else:
                st.warning("⚠️ Enter both username and password.")

# ------------------ Main App ------------------
if st.session_state['logged_in']:
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    page = st.sidebar.selectbox("Navigation", ["Dashboard", "Value Entry", "Report Generator"])

    if page == "Dashboard":
        st.title("📊 Dashboard")
        st.write("➡️ Use sidebar to navigate to Value Entry or Report Generator.")
    elif page == "Value Entry":
        st.title("🧪 Value Entry")
        try:
            from pages import value_entry
            value_entry.main()
        except Exception as e:
            st.error(f"⚠️ Value Entry page failed to load: {e}")
    elif page == "Report Generator":
        st.title("📄 Report Generator")
        try:
            from pages import report_generator
            report_generator.main()
        except Exception as e:
            st.error(f"⚠️ Report Generator page failed to load: {e}")

    # Logout Button
    if st.sidebar.button("🔓 Logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.stop() 
