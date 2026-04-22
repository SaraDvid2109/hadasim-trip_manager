"""
routes/students.py
------------------
כל ה-API endpoints הקשורים לתלמידות.

Routes:
    POST /api/students          — רישום תלמידה חדשה (למורות בלבד)
    GET  /api/students          — שליפת כל התלמידות (למורות בלבד)
    GET  /api/students/<id>     — שליפת תלמידה ספציפית (למורות בלבד)
"""

from flask import Blueprint, request, jsonify
from config import get_connection
from routes.teachers import verify_teacher   # ייבוא פונקציית האימות

students_bp = Blueprint("students", __name__)


# ── POST /api/students — רישום תלמידה חדשה ───────────────────────────────────
@students_bp.route("/api/students", methods=["POST"])
def register_student():
    """
    מקבלת JSON עם פרטי תלמידה ומכניסה אותה ל-DB.
    דורשת header: X-Teacher-ID (רק מורות יכולות לרשום תלמידות).
    
    Body (JSON):
        first_name, last_name, id_number (9 ספרות), class_name
    """
    teacher_id = request.headers.get("X-Teacher-ID")
    if not teacher_id or not verify_teacher(teacher_id):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    data = request.get_json()

    # ── וולידציה ─────────────────────────────────────────────────────────────
    required_fields = ["first_name", "last_name", "id_number", "class_name"]
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            return jsonify({"error": f"שדה חסר: {field}"}), 400

    id_number = str(data["id_number"]).strip()
    if not id_number.isdigit() or len(id_number) != 9:
        return jsonify({"error": "תעודת זהות חייבת להיות 9 ספרות"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO students (first_name, last_name, id_number, class_name)
            VALUES (%s, %s, %s, %s)
        """, (
            data["first_name"].strip(),
            data["last_name"].strip(),
            id_number,
            data["class_name"].strip()
        ))
        conn.commit()
        return jsonify({"message": "התלמידה נרשמה בהצלחה"}), 201

    except Exception as e:
        conn.rollback()
        if "23505" in str(e):
            return jsonify({"error": "תעודת זהות כבר רשומה במערכת"}), 409
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ── GET /api/students — שליפת כל התלמידות ────────────────────────────────────
@students_bp.route("/api/students", methods=["GET"])
def get_all_students():
    """
    מחזירה רשימה של כל התלמידות.
    דורשת header: X-Teacher-ID.
    """
    teacher_id = request.headers.get("X-Teacher-ID")
    if not teacher_id or not verify_teacher(teacher_id):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, id_number, class_name FROM students ORDER BY class_name, last_name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    students = [
        {"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]}
        for r in rows
    ]
    return jsonify(students), 200


# ── GET /api/students/<id_number> — שליפת תלמידה ספציפית ─────────────────────
@students_bp.route("/api/students/<id_number>", methods=["GET"])
def get_student(id_number):
    """
    מחזירה פרטים של תלמידה לפי תעודת זהות.
    דורשת header: X-Teacher-ID.
    """
    teacher_id = request.headers.get("X-Teacher-ID")
    if not teacher_id or not verify_teacher(teacher_id):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT first_name, last_name, id_number, class_name FROM students WHERE id_number = %s",
        (id_number,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "תלמידה לא נמצאה"}), 404

    return jsonify({
        "first_name": row[0], "last_name": row[1],
        "id_number": row[2], "class_name": row[3]
    }), 200
