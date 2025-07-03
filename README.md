# 🧠 AI Resume Improviser (Groq-Powered)

An AI-powered web app built with **Streamlit**, **Groq**, and **MongoDB** that improves your resume based on your target job role. Includes secure login, PDF extraction, and AI-generated feedback.

---

## 🚀 Features

- ✅ Upload resume in PDF format
- 🔐 Secure user login & registration (with password hashing)
- 🧾 Extract and preview resume text
- 🤖 Generate resume feedback using Groq LLaMA-3
- 💾 Save feedback to MongoDB per user
- ⚙️ Easily configurable with `.env`

---

## 📦 Tech Stack

| Layer         | Tech Used                            |
|---------------|--------------------------------------|
| Frontend      | Streamlit                            |
| Backend       | Python, Groq SDK                     |
| Auth/Security | `werkzeug.security`, `python-dotenv` |
| Database      | MongoDB (local or Atlas)             |
| File Handling | PyPDF2                               |

---

## 🛡️ Security & Authentication

### 🔐 User Accounts

- Secure login & registration using `werkzeug.security`
  - Passwords are hashed using `generate_password_hash()`
  - Login verified with `check_password_hash()`
- No plain-text passwords are stored in MongoDB

### 🗝️ Environment Variables

- All credentials are stored securely in a `.env` file:
  ```env
  GROQ_API_KEY=your_groq_api_key
  MONGO_URI=mongodb://localhost:27017/
