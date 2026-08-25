import os
import secrets
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import OpenAI
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from PyPDF2 import PdfReader

load_dotenv()

app = FastAPI(title="Resume Improviser API", version="2.0.0")
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "24"))
streamlit_url = os.getenv("STREAMLIT_URL", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = None
mongo_db = None
user_collection = None
resume_collection = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_db = mongo_client[os.getenv("MONGO_DATABASE", "resume_db")]
        user_collection = mongo_db["users"]
        resume_collection = mongo_db["resumes"]
    except PyMongoError as exc:
        print(f"MongoDB connection failed: {exc}")

temporary_users: dict[str, dict[str, str]] = {}
temporary_resumes: dict[str, dict[str, Any]] = {}


def find_user(username: str) -> dict[str, Any] | None:
    if user_collection is not None:
        return user_collection.find_one({"username": username}, {"_id": 0})
    return temporary_users.get(username)


def save_user(username: str, password: str) -> None:
    if user_collection is not None:
        user_collection.insert_one({"username": username, "password": password})
    else:
        temporary_users[username] = {"password": password}


def find_resume(resume_id: str) -> dict[str, Any] | None:
    if resume_collection is not None:
        return resume_collection.find_one({"id": resume_id}, {"_id": 0})
    return temporary_resumes.get(resume_id)


def save_resume(resume: dict[str, Any]) -> None:
    if resume_collection is not None:
        resume_collection.insert_one(dict(resume))
    else:
        temporary_resumes[resume["id"]] = resume


def save_versions(resume_id: str, versions: list[dict[str, Any]]) -> None:
    if resume_collection is not None:
        resume_collection.update_one({"id": resume_id}, {"$set": {"versions": versions}})
    elif resume_id in temporary_resumes:
        temporary_resumes[resume_id]["versions"] = versions


def list_user_resumes(username: str) -> list[dict[str, Any]]:
    if resume_collection is not None:
        return list(resume_collection.find({"username": username}, {"_id": 0}))
    return [resume for resume in temporary_resumes.values() if resume["username"] == username]


def remove_resume(resume_id: str) -> None:
    if resume_collection is not None:
        resume_collection.delete_one({"id": resume_id})
    elif resume_id in temporary_resumes:
        del temporary_resumes[resume_id]


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class RoleUpdate(BaseModel):
    job_role: str = Field(default="", max_length=160)


def create_token(username: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    return jwt.encode({"sub": username, "exp": expires}, SECRET_KEY, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if not username or find_user(username) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User authentication failed")
    return username


def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def improve_resume(resume_text: str, job_role: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured in .env file.")

    base_url = os.getenv("OPENAI_BASE_URL")
    try:
        client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
        model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")

        response = client.chat.completions.create(
            model=model,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional resume editor. Give practical, specific feedback in Markdown.",
                },
                {
                    "role": "user",
                    "content": f"Review this resume for {job_role or 'general job applications'}. Identify strengths, issues, and prioritized edits.\n\n{resume_text}",
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(exc)}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    db_status = "connected" if mongo_db is not None else "fallback_memory"
    return {"status": "ok", "database": db_status}


@app.post("/auth/register", status_code=201)
def register(credentials: Credentials) -> dict[str, str]:
    email = credentials.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if find_user(email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    save_user(email, pbkdf2_sha256.hash(credentials.password))
    return {"message": "Registration successful"}


@app.post("/auth/login")
def login(credentials: Credentials) -> dict[str, str]:
    email = credentials.email.strip().lower()
    user = find_user(email)
    if not user or not pbkdf2_sha256.verify(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(email), "token_type": "bearer"}


def owned_resume(resume_id: str, username: str) -> dict[str, Any]:
    resume = find_resume(resume_id)
    if not resume or resume["username"] != username:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@app.post("/resumes", status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    job_role: str = Form(default=""),
    username: str = Depends(current_user),
) -> dict[str, Any]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    text = extract_text(await file.read())
    if not text:
        raise HTTPException(status_code=422, detail="Could not extract text from this PDF")

    resume_id = secrets.token_urlsafe(12)
    resume = {
        "id": resume_id,
        "username": username,
        "filename": file.filename or "resume.pdf",
        "job_role": job_role.strip(),
        "resume_text": text,
        "versions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_resume(resume)
    return {"id": resume_id, "filename": resume["filename"], "job_role": resume["job_role"]}


@app.get("/resumes")
def list_resumes(username: str = Depends(current_user)) -> list[dict[str, Any]]:
    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "job_role": r["job_role"],
            "version_count": len(r["versions"]),
            "created_at": r["created_at"],
        }
        for r in list_user_resumes(username)
    ]


@app.get("/resumes/{resume_id}")
def get_resume(resume_id: str, username: str = Depends(current_user)) -> dict[str, Any]:
    resume = owned_resume(resume_id, username)
    return {k: v for k, v in resume.items() if k not in ("_id", "username")}


@app.get("/resumes/{resume_id}/versions")
def get_versions(resume_id: str, username: str = Depends(current_user)) -> list[dict[str, Any]]:
    return owned_resume(resume_id, username)["versions"]


@app.post("/resumes/{resume_id}/iterations", status_code=201)
def create_iteration(resume_id: str, username: str = Depends(current_user)) -> dict[str, Any]:
    resume = owned_resume(resume_id, username)
    feedback = improve_resume(resume["resume_text"], resume["job_role"])
    version = {
        "version": len(resume["versions"]) + 1,
        "feedback": feedback,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    resume["versions"].append(version)
    save_versions(resume_id, resume["versions"])
    return version


@app.put("/resumes/{resume_id}")
def update_resume(resume_id: str, update: RoleUpdate, username: str = Depends(current_user)) -> dict[str, str]:
    resume = owned_resume(resume_id, username)
    resume["job_role"] = update.job_role.strip()
    if resume_collection is not None:
        resume_collection.update_one({"id": resume_id}, {"$set": {"job_role": resume["job_role"]}})
    return {"id": resume_id, "job_role": resume["job_role"]}


@app.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: str, username: str = Depends(current_user)) -> None:
    owned_resume(resume_id, username)
    remove_resume(resume_id)
