import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DB_NAME = "exam_buddy_pro.db"

APP_SETTINGS = {
    "max_questions_per_quiz": 20,
    "default_exam_duration_minutes": 30,
    "theme": "professional"
}