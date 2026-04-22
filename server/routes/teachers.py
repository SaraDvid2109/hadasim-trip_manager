"""
routes/teachers.py
------------------
כל ה-API endpoints הקשורים למורות.

Routes:
    POST /api/teachers          — רישום מורה חדשה
    GET  /api/teachers          — שליפת כל המורות (למורות בלבד)
    GET  /api/teachers/<id>     — שליפת מורה ספציפית (למורות בלבד)
    GET  /api/teachers/<id>/students — שליפת תלמידות הכיתה של מורה (למורות בלבד)
"""

from flask import Blueprint, request, jsonify
from config import get_connection

# Blueprint = "מודול" של Flask. מאפשר לחלק את ה-routes לקבצים שונים.
teachers_bp = Blueprint("teachers", __name__)


def verify_teacher(id_number):
    """
    פונקציית עזר: בודקת אם תעודת זהות שייכת למורה קיימת ב-DB.
    מחזירה True אם המורה קיימת, False אם לא.
    
    זהו מנגנון ההגנה הפשוט שלנו — רק מורות יכולות לגשת לנתונים.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM teachers WHERE id_number = %s", (id_number,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None


# ── POST /api/teachers — רישום מורה חדשה ─────────────────────────────────────
@teachers_bp.route("/api/teachers", methods=["POST"])
def register_teacher():
    """
    מקבלת JSON עם פרטי מורה ומכניסה אותה ל-DB.
    
    Body (JSON):
        first_name, last_name, id_number (9 ספרות), class_name
    """
    data = request.get_json()

    # ── וולידציה — בדיקת שכל השדות קיימים ─────────────────────────────────
    required_fields = ["first_name", "last_name", "id_number", "class_name"]
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            return jsonify({"error": f"שדה חסר: {field}"}), 400

    # ── וולידציה — תעודת זהות חייבת להיות בדיוק 9 ספרות ───────────────────
    id_number = str(data["id_number"]).strip()
    if not id_number.isdigit() or len(id_number) != 9:
        return jsonify({"error": "תעודת זהות חייבת להיות 9 ספרות"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO teachers (first_name, last_name, id_number, class_name)
            VALUES (%s, %s, %s, %s)
        """, (
            data["first_name"].strip(),
            data["last_name"].strip(),
            id_number,
            data["class_name"].strip()
        ))
        conn.commit()
        return jsonify({"message": "המורה נרשמה בהצלחה"}), 201

    except Exception as e:
        conn.rollback()
        # שגיאה 23505 = unique violation = תעודת זהות כבר קיימת
        if "23505" in str(e):
            return jsonify({"error": "תעודת זהות כבר רשומה במערכת"}), 409
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ── GET /api/teachers — שליפת כל המורות ──────────────────────────────────────
@teachers_bp.route("/api/teachers", methods=["GET"])
def get_all_teachers():
    """
    מחזירה רשימה של כל המורות.
    דורשת header: X-Teacher-ID עם תעודת זהות של מורה מורשית.
    """
    teacher_id = request.headers.get("X-Teacher-ID")
    if not teacher_id or not verify_teacher(teacher_id):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, id_number, class_name FROM teachers ORDER BY last_name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    teachers = [
        {"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]}
        for r in rows
    ]
    return jsonify(teachers), 200


# ── GET /api/teachers/<id_number> — שליפת מורה ספציפית ──────────────────────
@teachers_bp.route("/api/teachers/<id_number>", methods=["GET"])
def get_teacher(id_number):
    """
    מחזירה פרטים של מורה לפי תעודת זהות.
    דורשת header: X-Teacher-ID.
    """
    teacher_id = request.headers.get("X-Teacher-ID")
    if not teacher_id or not verify_teacher(teacher_id):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT first_name, last_name, id_number, class_name FROM teachers WHERE id_number = %s",
        (id_number,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "מורה לא נמצאה"}), 404

    return jsonify({
        "first_name": row[0], "last_name": row[1],
        "id_number": row[2], "class_name": row[3]
    }), 200


# ── GET /api/teachers/<id_number>/students — תלמידות הכיתה של מורה ──────────
@teachers_bp.route("/api/teachers/<id_number>/students", methods=["GET"])
def get_teacher_students(id_number):
    """
    מחזירה רשימת כל התלמידות בכיתה של המורה שצוינה.
    שים לב: מחפשים לפי class_name — לכן כיתת המורה = כיתת התלמידות.
    דורשת header: X-Teacher-ID.
    """
    teacher_id = request.headers.get("X-Teacher-ID")
    if not teacher_id or not verify_teacher(teacher_id):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    # שולפים קודם את שם הכיתה של המורה
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT class_name FROM teachers WHERE id_number = %s", (id_number,))
    teacher = cursor.fetchone()

    if not teacher:
        cursor.close()
        conn.close()
        return jsonify({"error": "מורה לא נמצאה"}), 404

    class_name = teacher[0]

    # שולפים את כל התלמידות מאותה כיתה
    cursor.execute(
        "SELECT first_name, last_name, id_number, class_name FROM students WHERE class_name = %s ORDER BY last_name",
        (class_name,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    students = [
        {"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]}
        for r in rows
    ]
    return jsonify({"class": class_name, "students": students}), 200
