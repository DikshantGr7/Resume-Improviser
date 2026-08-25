import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def setting(name: str, default: str = "") -> str:
    """Read normal environment variables and Streamlit Cloud secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        if name in st.secrets:
            return str(st.secrets[name])
        return default
    except (FileNotFoundError, KeyError):
        return default


API_URL = setting("BACKEND_URL", setting("API_URL", "http://localhost:8000")).rstrip("/")

st.set_page_config(page_title="Resume Improviser", page_icon="📝", layout="wide")

st.markdown(
    """
<style>
div[data-testid="stAppViewContainer"], .main, [data-testid="stHeader"] {
    transition: none !important;
    animation: none !important;
}
.stApp {
    background-color: #0e1117 !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] {
    background-color: #161b22 !important;
}
.hero {
    padding: 1rem 0;
    border-bottom: 1px solid #30363d;
    margin-bottom: 1.5rem;
}
.hero h1 {
    color: #58a6ff !important;
    font-size: 2.2rem;
    font-weight: 700;
    margin: 0;
}
.hero p {
    color: #8b949e !important;
    margin-top: 0.2rem;
}
.auth-panel {
    background: #161b22;
    border: 1px solid #30363d;
    padding: 1.5rem;
    border-radius: 8px;
}
div[data-baseweb="input"] > div {
    background-color: #0d1117 !important;
    color: #ffffff !important;
    border-color: #30363d !important;
}
input {
    color: #ffffff !important;
}
label, p, span, h1, h2, h3 {
    color: #f0f6fc !important;
}
.stButton > button {
    border-radius: 6px;
    transition: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

if "token" not in st.session_state:
    st.session_state.token = None
if "resume_id" not in st.session_state:
    st.session_state.resume_id = None


def api_request(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=120, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Request failed")
        except ValueError:
            detail = response.text or "Request failed"
        raise RuntimeError(detail)
    return response.json() if response.content else None


def auth_screen():
    st.markdown(
        '<div class="hero"><h1>Resume Improviser</h1><p>Sharper resumes, one deliberate iteration at a time.</p></div>',
        unsafe_allow_html=True,
    )
    mode = st.radio("Account access", ["Log in", "Sign up"], horizontal=True, label_visibility="collapsed")

    st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
    if mode == "Log in":
        st.subheader("Log in to your account")
        with st.form("login_form"):
            email = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submitted:
            try:
                result = api_request("POST", "/auth/login", json={"email": email, "password": password})
                st.session_state.token = result["access_token"]
                st.rerun()
            except (RuntimeError, requests.RequestException) as exc:
                st.error(str(exc))
    else:
        st.subheader("Create your account")
        with st.form("register_form"):
            email = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="At least 8 characters")
            submitted = st.form_submit_button("Sign up", type="primary", use_container_width=True)
        if submitted:
            try:
                api_request("POST", "/auth/register", json={"email": email, "password": password})
                st.success("Account created. Log in to continue.")
            except (RuntimeError, requests.RequestException) as exc:
                st.error(str(exc))
    st.markdown("</div>", unsafe_allow_html=True)


def workspace():
    st.markdown(
        '<div class="hero"><h1>Resume Workspace</h1><p>Upload once. Improve through focused iterations.</p></div>',
        unsafe_allow_html=True,
    )

    header_col, signout_col = st.columns([5, 1])
    with signout_col:
        if st.button("Sign out", use_container_width=True):
            st.session_state.token = None
            st.session_state.resume_id = None
            st.rerun()

    try:
        resumes = api_request("GET", "/resumes")
    except (RuntimeError, requests.RequestException) as exc:
        st.error(f"Failed to fetch resumes: {exc}")
        return

    with st.sidebar:
        st.subheader("Your Resumes")
        if not resumes:
            st.caption("No resumes uploaded yet.")
        for r in resumes:
            label = f"📄 {r['filename']} ({r['version_count']})"
            if st.button(label, key=f"select_{r['id']}", use_container_width=True):
                st.session_state.resume_id = r["id"]
                st.rerun()

    if not st.session_state.resume_id:
        st.subheader("Start with a PDF")
        uploaded = st.file_uploader("Upload PDF Resume", type=["pdf"], label_visibility="collapsed")
        role = st.text_input("Target Job Role", placeholder="e.g. Senior Data Analyst")

        if uploaded and st.button("Upload Resume", type="primary"):
            try:
                with st.spinner("Processing PDF..."):
                    result = api_request(
                        "POST",
                        "/resumes",
                        files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                        data={"job_role": role},
                    )
                    st.session_state.resume_id = result["id"]
                    st.rerun()
            except (RuntimeError, requests.RequestException) as exc:
                st.error(str(exc))
        return

    try:
        resume = api_request("GET", f"/resumes/{st.session_state.resume_id}")
        versions = api_request("GET", f"/resumes/{st.session_state.resume_id}/versions")
    except (RuntimeError, requests.RequestException) as exc:
        st.error(f"Error fetching resume: {exc}")
        st.session_state.resume_id = None
        return

    with st.form("role_form"):
        role_col, btn_col = st.columns([4, 1])
        with role_col:
            updated_role = st.text_input("Target role", value=resume.get("job_role", ""), key="role_val")
        with btn_col:
            st.write("")
            st.write("")
            saved = st.form_submit_button("Save Role", use_container_width=True)
        if saved:
            try:
                api_request("PUT", f"/resumes/{resume['id']}", json={"job_role": updated_role})
                st.toast("Role saved for this resume!", icon="✅")
            except (RuntimeError, requests.RequestException) as exc:
                st.error(str(exc))

    if st.button("Generate Next Feedback Iteration", type="primary", use_container_width=True):
        with st.spinner("Analyzing resume with AI..."):
            try:
                api_request("POST", f"/resumes/{resume['id']}/iterations")
                st.rerun()
            except (RuntimeError, requests.RequestException) as exc:
                st.error(f"Feedback generation error: {exc}")

    st.subheader(f"Feedback History ({len(versions)} iterations)")
    if not versions:
        st.info("No feedback generated yet. Click above to generate your first review.")
    else:
        for version in reversed(versions):
            timestamp = version["created_at"][:16].replace("T", " ")
            with st.expander(f"Iteration {version['version']} · {timestamp}", expanded=(version == versions[-1])):
                st.markdown(version["feedback"])

    with st.expander("Extracted Resume Text"):
        st.text(resume.get("resume_text", ""))

    st.divider()
    if st.button("Delete Resume", type="secondary"):
        try:
            api_request("DELETE", f"/resumes/{resume['id']}")
            st.session_state.resume_id = None
            st.rerun()
        except (RuntimeError, requests.RequestException) as exc:
            st.error(str(exc))


if st.session_state.token:
    workspace()
else:
    auth_screen()
