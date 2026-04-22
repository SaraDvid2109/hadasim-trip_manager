import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

def get_connection():
    """
    יוצרת חיבור חדש לבסיס הנתונים PostgreSQL.
    מחזירה אובייקט connection שאיתו נוכל לשלוח שאילתות.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn
