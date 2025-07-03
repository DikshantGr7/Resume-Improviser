import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("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")

client = Groq(api_key=GROQ_API_KEY)

def get_improved_resume(file_text, job_role=None):
    prompt = f"""Please analyze this resume and provide constructive feedback.
Focus on:
1. Content clarity and impact
2. Skills presentation
3. Experience descriptions
4. Improvements for {job_role if job_role else 'general job applications'}

Resume content:
{file_text}
"""

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are a professional HR assistant helping improve resumes."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()
