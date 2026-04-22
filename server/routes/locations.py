"""
routes/locations.py
-------------------
API endpoints לניהול מיקומי תלמידות (שלב ב').

Routes:
    POST /api/location          — קבלת מיקום ממכשיר האיכון
    GET  /api/locations         — שליפת המיקום האחרון של כל תלמידה
    POST /api/location/teacher  — שלב ג': בדיקת תלמידות שהתרחקו מהמורה
"""

from flask import Blueprint, request, jsonify
from config import get_connection
from routes.teachers import verify_teacher
import math

locations_bp = Blueprint("locations", __name__)


def dms_to_decimal(degrees, minutes, seconds):
    """
    ממירה קואורדינטות מפורמט DMS לפורמט Decimal Degrees.
    
    דוגמה: 32° 5' 23" → 32 + 5/60 + 23/3600 = 32.0897...
    
    Leaflet.js (ספריית המפות) דורשת Decimal Degrees — לכן ההמרה הזו הכרחית.
    """
    return float(degrees) + float(minutes) / 60 + float(seconds) / 3600


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    מחשבת מרחק אווירי בין שתי נקודות גיאוגרפיות בקילומטרים.
    משתמשת בנוסחת Haversine שמתחשבת בעובדה שכדור הארץ עגול.
    
    פרמטרים: רוחב/אורך של שתי נקודות (Decimal Degrees)
    מחזירה: מרחק בקילומטרים
    
    משמש בשלב ג' — לבדוק אם תלמידה רחוקה יותר מ-3 ק"מ מהמורה.
    """
    R = 6371  # רדיוס כדור הארץ בקילומטרים

    # המרה לרדיאנים (נוסחת Haversine דורשת רדיאנים)
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


# ── POST /api/location — קבלת עדכון מיקום ────────────────────────────────────
@locations_bp.route("/api/location", methods=["POST"])
def receive_location():
    """
    מקבלת JSON ממכשיר האיכון ושומרת ב-DB.
    
    פורמט ה-JSON (כפי שמוגדר בתרגיל):
    {
        "ID": 123456789,
        "Coordinates": {
            "Longitude": {"Degrees": "34", "Minutes": "46", "Seconds": "44"},
            "Latitude":  {"Degrees": "32", "Minutes": "5",  "Seconds": "23"}
        },
        "Time": "2024-12-05T15:30:00Z"
    }
    """
    data = request.get_json()

    try:
        student_id = str(data["ID"]).zfill(9)   # משלימים ל-9 ספרות אם צריך
        lon = data["Coordinates"]["Longitude"]
        lat = data["Coordinates"]["Latitude"]
        recorded_at = data["Time"]

        conn = get_connection()
        cursor = conn.cursor()

        # בדיקה שהתלמידה קיימת ב-DB לפני שמרים מיקום
        cursor.execute("SELECT 1 FROM students WHERE id_number = %s", (student_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "תלמידה לא נמצאה"}), 404

        cursor.execute("""
            INSERT INTO locations 
                (student_id_number, lon_degrees, lon_minutes, lon_seconds,
                 lat_degrees, lat_minutes, lat_seconds, recorded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            int(lon["Degrees"]), int(lon["Minutes"]), int(lon["Seconds"]),
            int(lat["Degrees"]), int(lat["Minutes"]), int(lat["Seconds"]),
            recorded_at
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "מיקום נשמר בהצלחה"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── GET /api/locations — המיקום האחרון של כל תלמידה ─────────────────────────
@locations_bp.route("/api/locations", methods=["GET"])
def get_latest_locations():
    """
    מחזירה את המיקום הכי עדכני של כל תלמידה.
    
    משתמשים ב-DISTINCT ON — תכונה של PostgreSQL שמחזירה שורה אחת לכל ערך ייחודי.
    כאן: שורה אחת לכל תלמידה — הכי עדכנית לפי recorded_at.
    
    מחזיר קואורדינטות ב-Decimal Degrees (אחרי המרה) עבור Leaflet.js.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # DISTINCT ON (student_id_number) + ORDER BY recorded_at DESC =
    # "תחזיר את הרשומה הכי חדשה לכל תלמידה"
    cursor.execute("""
        SELECT DISTINCT ON (l.student_id_number)
            l.student_id_number,
            s.first_name,
            s.last_name,
            s.class_name,
            l.lon_degrees, l.lon_minutes, l.lon_seconds,
            l.lat_degrees, l.lat_minutes, l.lat_seconds,
            l.recorded_at
        FROM locations l
        JOIN students s ON s.id_number = l.student_id_number
        ORDER BY l.student_id_number, l.recorded_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    result = []
    for row in rows:
        # המרה מ-DMS ל-Decimal Degrees
        longitude = dms_to_decimal(row[4], row[5], row[6])
        latitude  = dms_to_decimal(row[7], row[8], row[9])

        result.append({
            "id_number":   row[0],
            "first_name":  row[1],
            "last_name":   row[2],
            "class_name":  row[3],
            "longitude":   longitude,
            "latitude":    latitude,
            "recorded_at": row[10].isoformat() if row[10] else None
        })

    return jsonify(result), 200


# ── POST /api/location/teacher — שלב ג': בדיקת מרחק ─────────────────────────
@locations_bp.route("/api/location/teacher", methods=["POST"])
def check_distance_from_teacher():
    """
    שלב ג' (בונוס): מקבלת מיקום המורה ומחזירה אילו תלמידות רחוקות יותר מ-3 ק"מ.
    
    Body: אותו פורמט JSON כמו מכשיר האיכון של תלמידה.
    דורשת header: X-Teacher-ID.
    
    הלוגיקה:
    1. קוראת מיקום המורה מה-body
    2. שולפת המיקום האחרון של כל תלמידה מה-DB
    3. מחשבת מרחק בין המורה לכל תלמידה בנוסחת Haversine
    4. מחזירה רשימה של תלמידות שמרחקן > 3 ק"מ
    """
    teacher_id = request.headers.get("X-Teacher-ID")
    if not teacher_id or not verify_teacher(teacher_id):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    data = request.get_json()

    try:
        # מיקום המורה
        t_lon = data["Coordinates"]["Longitude"]
        t_lat = data["Coordinates"]["Latitude"]
        teacher_lat = dms_to_decimal(t_lat["Degrees"], t_lat["Minutes"], t_lat["Seconds"])
        teacher_lon = dms_to_decimal(t_lon["Degrees"], t_lon["Minutes"], t_lon["Seconds"])

    except (KeyError, ValueError):
        return jsonify({"error": "פורמט מיקום שגוי"}), 400

    # שליפת המיקום הכי עדכני של כל תלמידה
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT ON (l.student_id_number)
            l.student_id_number,
            s.first_name, s.last_name, s.class_name,
            l.lon_degrees, l.lon_minutes, l.lon_seconds,
            l.lat_degrees, l.lat_minutes, l.lat_seconds,
            l.recorded_at
        FROM locations l
        JOIN students s ON s.id_number = l.student_id_number
        ORDER BY l.student_id_number, l.recorded_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    far_students = []
    DISTANCE_THRESHOLD_KM = 3.0

    for row in rows:
        student_lon = dms_to_decimal(row[4], row[5], row[6])
        student_lat = dms_to_decimal(row[7], row[8], row[9])

        distance = haversine_distance(teacher_lat, teacher_lon, student_lat, student_lon)

        if distance > DISTANCE_THRESHOLD_KM:
            far_students.append({
                "id_number":   row[0],
                "first_name":  row[1],
                "last_name":   row[2],
                "class_name":  row[3],
                "longitude":   student_lon,
                "latitude":    student_lat,
                "distance_km": round(distance, 2),
                "recorded_at": row[10].isoformat() if row[10] else None
            })

    return jsonify({
        "teacher_location": {"latitude": teacher_lat, "longitude": teacher_lon},
        "far_students": far_students,
        "threshold_km": DISTANCE_THRESHOLD_KM
    }), 200
