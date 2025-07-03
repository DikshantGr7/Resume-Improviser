import streamlit as st
from extractor import extract_text_from_pdf
from api_handler import get_improved_resume
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["resume_db"]
users = db["users"]
history = db["history"]

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ---------- Authentication Logic ----------
def login(username, password):
    user = users.find_one({"username": username})
    if user and user["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.page = "app"
        return True
    return False

def register(username, password):
    if users.find_one({"username": username}):
        return False
    users.insert_one({"username": username, "password": password})
    return True

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.page = "login"

# ---------- UI Screens ----------
def show_login():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.success("✅ Logged in successfully!")
        else:
            st.error("❌ Invalid username or password.")

    st.markdown("---")
    st.write("Don't have an account?")
    if st.button("Go to Register"):
        st.session_state.page = "register"

def show_register():
    st.title("📝 Register")
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")
    if st.button("Register"):
        if register(username, password):
            st.success("✅ Registered successfully! You can now log in.")
            st.session_state.page = "login"
        else:
            st.error("❌ Username already exists.")
    st.markdown("---")
    if st.button("Back to Login"):
        st.session_state.page = "login"

def show_main_app():
    st.title("📄 AI Resume Improviser")
    st.write(f"Welcome, **{st.session_state.username}**!")
    if st.button("🔓 Logout"):
        logout()
        st.experimental_rerun()

    uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")
    job_role = st.text_input("Enter the job role you're applying for (optional)")

    if uploaded_file is not None:
        st.success("✅ File uploaded successfully.")
        file_text = extract_text_from_pdf(uploaded_file)

        print("Extracted text:")
        print(file_text)

        st.subheader("📄 Resume Text Preview")
        st.write(file_text[:500] if file_text else "No text extracted.")

        if file_text.strip():
            try:
                result = get_improved_resume(file_text, job_role)

                print("AI Response:")
                print(result)

                if result:
                    st.subheader("✨ AI Suggestions")
                    st.markdown(result)

                    # Save to MongoDB
                    history.insert_one({
                        "username": st.session_state.username,
                        "timestamp": datetime.datetime.now(),
                        "job_role": job_role,
                        "resume_text": file_text,
                        "ai_feedback": result
                    })
                    st.success("📌 Feedback saved to your history.")
                else:
                    st.warning("⚠️ No response generated. Check API key or quota.")
            except Exception as e:
                st.error("❌ Error generating suggestions.")
                st.exception(e)
        else:
            st.warning("⚠️ Could not extract any text. Try another file.")

# ---------- Render Appropriate Page ----------
if st.session_state.page == "login":
    show_login()
elif st.session_state.page == "register":
    show_register()
else:
    show_main_app()
