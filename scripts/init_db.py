import psycopg2, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "server" / ".env")

def conn(dbname=None):
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=dbname or os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD")
    )

def run_sql(*statements):
    c = conn(); cur = c.cursor()
    for sql in statements:
        cur.execute(sql)
    c.commit(); cur.close(); c.close()

if __name__ == "__main__":
    c = conn("postgres"); c.autocommit = True; cur = c.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname='hadasim_trip'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE hadasim_trip")
        print("[OK] Database נוצר")
    else:
        print("[INFO] Database כבר קיים")
    cur.close(); c.close()

    run_sql(
        """CREATE TABLE IF NOT EXISTS teachers (
            id SERIAL PRIMARY KEY, first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL, id_number CHAR(9) NOT NULL UNIQUE, class_name VARCHAR(20) NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY, first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL, id_number CHAR(9) NOT NULL UNIQUE, class_name VARCHAR(20) NOT NULL
        )""",
        # קואורדינטות נשמרות ב-DMS כפי שמגיעות ממכשיר האיכון
        """CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY, student_id_number CHAR(9) NOT NULL,
            lon_degrees INTEGER NOT NULL, lon_minutes INTEGER NOT NULL, lon_seconds INTEGER NOT NULL,
            lat_degrees INTEGER NOT NULL, lat_minutes INTEGER NOT NULL, lat_seconds INTEGER NOT NULL,
            recorded_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id_number) REFERENCES students(id_number)
        )"""
    )
    print("[OK] אתחול הושלם")
