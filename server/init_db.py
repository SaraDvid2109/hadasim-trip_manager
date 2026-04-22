"""
init_db.py
----------
סקריפט זה יוצר את מסד הנתונים ואת הטבלאות הדרושות.
יש להריץ אותו פעם אחת לפני הפעלת השרת:
    python init_db.py
"""

import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# טוען את .env מאותה תיקיה שבה נמצא הסקריפט (server/)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

def create_database():
    """
    מתחברת ל-PostgreSQL ויוצרת את ה-database 'hadasim_trip' אם לא קיים.
    נתחבר קודם ל-database הברירת מחדל (postgres) כדי ליצור DB חדש.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname="postgres",           # DB ברירת מחדל — תמיד קיים
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    conn.autocommit = True           # יצירת DB דורשת autocommit
    cursor = conn.cursor()

    # בדיקה אם ה-DB כבר קיים
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'hadasim_trip'")
    exists = cursor.fetchone()

    if not exists:
        cursor.execute("CREATE DATABASE hadasim_trip")
        print("[OK] Database 'hadasim_trip' נוצר בהצלחה")
    else:
        print("[INFO] Database 'hadasim_trip' כבר קיים")

    cursor.close()
    conn.close()


def create_tables():
    """
    יוצרת את כל הטבלאות הדרושות:
    - teachers: מורות
    - students: תלמידות
    - locations: מיקומי התלמידות (מתעדכן כל דקה)
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cursor = conn.cursor()

    # ── טבלת מורות ──────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id          SERIAL PRIMARY KEY,
            first_name  VARCHAR(50)  NOT NULL,
            last_name   VARCHAR(50)  NOT NULL,
            id_number   CHAR(9)      NOT NULL UNIQUE,   -- תעודת זהות, 9 ספרות
            class_name  VARCHAR(20)  NOT NULL            -- שם הכיתה (לדוג': ו'1)
        );
    """)

    # ── טבלת תלמידות ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          SERIAL PRIMARY KEY,
            first_name  VARCHAR(50)  NOT NULL,
            last_name   VARCHAR(50)  NOT NULL,
            id_number   CHAR(9)      NOT NULL UNIQUE,   -- תעודת זהות, 9 ספרות
            class_name  VARCHAR(20)  NOT NULL
        );
    """)

    # ── טבלת מיקומים ────────────────────────────────────────────────────────
    # כל שורה = עדכון מיקום אחד שהגיע ממכשיר האיכון
    # הקואורדינטות נשמרות בפורמט DMS (Degrees, Minutes, Seconds)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id                   SERIAL PRIMARY KEY,
            student_id_number    CHAR(9)      NOT NULL,  -- מזהה התלמידה
            lon_degrees          INTEGER      NOT NULL,   -- אורך גיאוגרפי - מעלות
            lon_minutes          INTEGER      NOT NULL,   -- אורך גיאוגרפי - דקות
            lon_seconds          INTEGER      NOT NULL,   -- אורך גיאוגרפי - שניות
            lat_degrees          INTEGER      NOT NULL,   -- רוחב גיאוגרפי - מעלות
            lat_minutes          INTEGER      NOT NULL,   -- רוחב גיאוגרפי - דקות
            lat_seconds          INTEGER      NOT NULL,   -- רוחב גיאוגרפי - שניות
            recorded_at          TIMESTAMP    NOT NULL,   -- זמן עדכון המיקום
            FOREIGN KEY (student_id_number) REFERENCES students(id_number)
        );
    """)

    conn.commit()
    print("[OK] כל הטבלאות נוצרו בהצלחה")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    print("[*] מאתחל את מסד הנתונים...")
    create_database()
    create_tables()
    print("[OK] אתחול הושלם!")
