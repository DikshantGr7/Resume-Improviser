from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  

client = MongoClient(os.getenv("mongodb://localhost:27017/"))
db = client["resume_db"]
collection = db["resumes"]

def save_to_db(username, original, improved, role):
    collection.insert_one({
        "user": username,
        "role": role,
        "original_resume": original,
        "improved_resume": improved,
        "timestamp": datetime.now()
    })
