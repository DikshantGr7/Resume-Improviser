from pymongo import MongoClient
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()  # Load .env file

client = MongoClient(os.getenv("mongodb://localhost:27017/"))
db = client["resume_db"]
users = db["users"]

def register_user(username, password):
    if users.find_one({"username": username}):
        return "User already exists"
    users.insert_one({
        "username": username,
        "password": generate_password_hash(password)
    })
    return "Registration successful"

def login_user(username, password):
    user = users.find_one({"username": username})
    if user and check_password_hash(user['password'], password):
        return True
    return False
