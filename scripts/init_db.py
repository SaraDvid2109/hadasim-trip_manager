import psycopg2, os
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

def db_connection(dbname=None):
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), 
        port=os.getenv("DB_PORT"),
        dbname=dbname or os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"), 
        password=os.getenv("DB_PASSWORD")
    )

def initialize_database():
    create_teachers = """
        CREATE TABLE IF NOT EXISTS teachers (
            first_name VARCHAR(50) NOT NULL,
            last_name  VARCHAR(50) NOT NULL,
            id_number  CHAR(9) PRIMARY KEY,
            class_name VARCHAR(20) NOT NULL
        )"""
    create_students = """
        CREATE TABLE IF NOT EXISTS students (
            first_name VARCHAR(50) NOT NULL,
            last_name  VARCHAR(50) NOT NULL,
            id_number  CHAR(9) PRIMARY KEY,
            class_name VARCHAR(20) NOT NULL
        )"""
    create_locations = """
        CREATE TABLE IF NOT EXISTS locations (
            id               SERIAL PRIMARY KEY,
            student_id_number CHAR(9) NOT NULL,
            lon_degrees INTEGER NOT NULL, lon_minutes INTEGER NOT NULL, lon_seconds INTEGER NOT NULL,
            lat_degrees INTEGER NOT NULL, lat_minutes INTEGER NOT NULL, lat_seconds INTEGER NOT NULL,
            recorded_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id_number) REFERENCES students(id_number)
        )"""
    try:
        with db_connection() as c:
            with c.cursor() as cur:
                cur.execute(create_teachers)
                cur.execute(create_students)
                cur.execute(create_locations)
                c.commit()
        print("[OK] Initialization complete")
    except Exception as e:
        print(f"[Error] Initialization failed: {e}")

if __name__ == "__main__":
    try:
        c = db_connection("postgres"); c.autocommit = True
        with c.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (os.getenv("DB_NAME"),))
            if not cur.fetchone():
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(os.getenv("DB_NAME"))))
                print("[OK] Database created")
            else:
                print("[INFO] Database already exists")
        c.close()
    except Exception as e:
        print(f"[Warning] Could not ensure DB existence: {e}")
    
    initialize_database()
