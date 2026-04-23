"""
app.py — מערכת ניהול טיול שנתי
כל השרת בקובץ אחד: חיבור DB, routes מורות, תלמידות ומיקומים.
הרצה: python app.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2, os, math
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

app = Flask(__name__)
CORS(app)


# ── חיבור ל-DB ───────────────────────────────────────────────────────────────

def get_connection():
    """מחזירה חיבור חדש ל-PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# ── פונקציות עזר ─────────────────────────────────────────────────────────────

def verify_teacher(id_number):
    """בודקת אם תעודת הזהות שייכת למורה קיימת. מחזירה True/False."""
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT 1 FROM teachers WHERE id_number = %s", (id_number,))
    result = cur.fetchone()
    cur.close(); conn.close()
    return result is not None

def dms_to_decimal(d, m, s):
    """ממירה קואורדינטות DMS לעשרוני (Decimal Degrees) — נדרש עבור Leaflet.js."""
    return float(d) + float(m) / 60 + float(s) / 3600

def haversine(lat1, lon1, lat2, lon2):
    """מחשבת מרחק אווירי בק"מ בין שתי נקודות (נוסחת Haversine)."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return R * 2 * math.asin(math.sqrt(a))


# ── בריאות ───────────────────────────────────────────────────────────────────

@app.route("/")
def health():
    return {"status": "ok", "message": "מערכת ניהול הטיול פעילה ✅"}, 200


# ══ שלב א': מורות ════════════════════════════════════════════════════════════

@app.route("/api/teachers", methods=["POST"])
def register_teacher():
    """רישום מורה חדשה. קלט JSON: first_name, last_name, id_number, class_name."""
    data = request.get_json()
    for f in ["first_name", "last_name", "id_number", "class_name"]:
        if not str(data.get(f, "")).strip():
            return jsonify({"error": f"שדה חסר: {f}"}), 400
    id_num = str(data["id_number"]).strip()
    if not id_num.isdigit() or len(id_num) != 9:
        return jsonify({"error": "תעודת זהות חייבת להיות 9 ספרות"}), 400
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO teachers(first_name,last_name,id_number,class_name) VALUES(%s,%s,%s,%s)",
            (data["first_name"].strip(), data["last_name"].strip(), id_num, data["class_name"].strip())
        )
        conn.commit()
        return jsonify({"message": "המורה נרשמה בהצלחה"}), 201
    except Exception as e:
        conn.rollback()
        return (jsonify({"error": "תעודת זהות כבר רשומה במערכת"}), 409) if "23505" in str(e) else (jsonify({"error": str(e)}), 500)
    finally:
        cur.close(); conn.close()


@app.route("/api/teachers", methods=["GET"])
def get_all_teachers():
    """שליפת כל המורות. דורש Header: X-Teacher-ID."""
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT first_name,last_name,id_number,class_name FROM teachers ORDER BY last_name")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]} for r in rows])


@app.route("/api/teachers/<id_number>", methods=["GET"])
def get_teacher(id_number):
    """שליפת מורה ספציפית לפי ת.ז. דורש Header: X-Teacher-ID."""
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT first_name,last_name,id_number,class_name FROM teachers WHERE id_number=%s", (id_number,))
    r = cur.fetchone(); cur.close(); conn.close()
    if not r:
        return jsonify({"error": "מורה לא נמצאה"}), 404
    return jsonify({"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]})


@app.route("/api/teachers/<id_number>/students", methods=["GET"])
def get_teacher_students(id_number):
    """שליפת כל התלמידות בכיתה של מורה מסוימת. דורש Header: X-Teacher-ID."""
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT class_name FROM teachers WHERE id_number=%s", (id_number,))
    t = cur.fetchone()
    if not t:
        cur.close(); conn.close()
        return jsonify({"error": "מורה לא נמצאה"}), 404
    cur.execute(
        "SELECT first_name,last_name,id_number,class_name FROM students WHERE class_name=%s ORDER BY last_name",
        (t[0],)
    )
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify({"class": t[0], "students": [{"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]} for r in rows]})


# ══ שלב א': תלמידות ══════════════════════════════════════════════════════════

@app.route("/api/students", methods=["POST"])
def register_student():
    """רישום תלמידה חדשה. דורש Header: X-Teacher-ID."""
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    data = request.get_json()
    for f in ["first_name", "last_name", "id_number", "class_name"]:
        if not str(data.get(f, "")).strip():
            return jsonify({"error": f"שדה חסר: {f}"}), 400
    id_num = str(data["id_number"]).strip()
    if not id_num.isdigit() or len(id_num) != 9:
        return jsonify({"error": "תעודת זהות חייבת להיות 9 ספרות"}), 400
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO students(first_name,last_name,id_number,class_name) VALUES(%s,%s,%s,%s)",
            (data["first_name"].strip(), data["last_name"].strip(), id_num, data["class_name"].strip())
        )
        conn.commit()
        return jsonify({"message": "התלמידה נרשמה בהצלחה"}), 201
    except Exception as e:
        conn.rollback()
        return (jsonify({"error": "תעודת זהות כבר רשומה במערכת"}), 409) if "23505" in str(e) else (jsonify({"error": str(e)}), 500)
    finally:
        cur.close(); conn.close()


@app.route("/api/students", methods=["GET"])
def get_all_students():
    """שליפת כל התלמידות. דורש Header: X-Teacher-ID."""
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT first_name,last_name,id_number,class_name FROM students ORDER BY class_name, last_name")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]} for r in rows])


@app.route("/api/students/<id_number>", methods=["GET"])
def get_student(id_number):
    """שליפת תלמידה ספציפית לפי ת.ז. דורש Header: X-Teacher-ID."""
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT first_name,last_name,id_number,class_name FROM students WHERE id_number=%s", (id_number,))
    r = cur.fetchone(); cur.close(); conn.close()
    if not r:
        return jsonify({"error": "תלמידה לא נמצאה"}), 404
    return jsonify({"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]})


# ══ שלב ב': מיקומים ══════════════════════════════════════════════════════════

@app.route("/api/location", methods=["POST"])
def receive_location():
    """
    קבלת עדכון מיקום ממכשיר האיכון.
    פורמט: { "ID": 9ספרות, "Coordinates": { "Longitude": {D,M,S}, "Latitude": {D,M,S} }, "Time": ISO }
    """
    data = request.get_json()
    try:
        sid = str(data["ID"]).zfill(9)
        lon = data["Coordinates"]["Longitude"]
        lat = data["Coordinates"]["Latitude"]
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT 1 FROM students WHERE id_number=%s", (sid,))
        if not cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"error": "תלמידה לא נמצאה"}), 404
        cur.execute(
            "INSERT INTO locations(student_id_number,lon_degrees,lon_minutes,lon_seconds,lat_degrees,lat_minutes,lat_seconds,recorded_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (sid, int(lon["Degrees"]), int(lon["Minutes"]), int(lon["Seconds"]),
             int(lat["Degrees"]), int(lat["Minutes"]), int(lat["Seconds"]), data["Time"])
        )
        conn.commit(); cur.close(); conn.close()
        return jsonify({"message": "מיקום נשמר בהצלחה"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/locations", methods=["GET"])
def get_latest_locations():
    """
    שליפת המיקום האחרון של כל תלמידה.
    דורש Header: X-Teacher-ID — מורות בלבד.
    """
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (l.student_id_number)
            l.student_id_number, s.first_name, s.last_name, s.class_name,
            l.lon_degrees, l.lon_minutes, l.lon_seconds,
            l.lat_degrees, l.lat_minutes, l.lat_seconds, l.recorded_at
        FROM locations l
        JOIN students s ON s.id_number = l.student_id_number
        ORDER BY l.student_id_number, l.recorded_at DESC
    """)
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{
        "id_number": r[0], "first_name": r[1], "last_name": r[2], "class_name": r[3],
        "longitude": dms_to_decimal(r[4], r[5], r[6]),
        "latitude":  dms_to_decimal(r[7], r[8], r[9]),
        "recorded_at": (r[10].isoformat() + "+00:00") if r[10] else None
    } for r in rows])


# ══ שלב ג': בדיקת מרחק ═══════════════════════════════════════════════════════

@app.route("/api/location/teacher", methods=["POST"])
def check_distance():
    """
    שלב ג' (בונוס): מקבלת מיקום המורה + סף מרחק אופציונלי,
    מחשבת מרחק Haversine לכל תלמידה ומחזירה מי חרגה.
    עיקרון OCP: הסף מוגדר ע"י הקורא — הקוד סגור לשינוי, פתוח להרחבה.
    דורש Header: X-Teacher-ID.
    """
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
    data = request.get_json()

    # סף המרחק — ניתן להגדרה על ידי הקורא; ברירת מחדל 3 ק"מ (דרישת התרגיל)
    threshold_km = float(data.get("threshold_km", 3.0))

    try:
        tlon = data["Coordinates"]["Longitude"]
        tlat = data["Coordinates"]["Latitude"]
        t_lat = dms_to_decimal(tlat["Degrees"], tlat["Minutes"], tlat["Seconds"])
        t_lon = dms_to_decimal(tlon["Degrees"], tlon["Minutes"], tlon["Seconds"])
    except (KeyError, ValueError):
        return jsonify({"error": "פורמט מיקום שגוי"}), 400

    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (l.student_id_number)
            l.student_id_number, s.first_name, s.last_name, s.class_name,
            l.lon_degrees, l.lon_minutes, l.lon_seconds,
            l.lat_degrees, l.lat_minutes, l.lat_seconds, l.recorded_at
        FROM locations l
        JOIN students s ON s.id_number = l.student_id_number
        ORDER BY l.student_id_number, l.recorded_at DESC
    """)
    rows = cur.fetchall(); cur.close(); conn.close()

    far = []
    for r in rows:
        s_lon = dms_to_decimal(r[4], r[5], r[6])
        s_lat = dms_to_decimal(r[7], r[8], r[9])
        d = haversine(t_lat, t_lon, s_lat, s_lon)
        if d > threshold_km:   # <-- משתנה, לא קבוע קשיח
            far.append({
                "id_number": r[0], "first_name": r[1], "last_name": r[2], "class_name": r[3],
                "longitude": s_lon, "latitude": s_lat,
                "distance_km": round(d, 2),
                "recorded_at": (r[10].isoformat() + "+00:00") if r[10] else None
            })

    return jsonify({
        "teacher_location": {"latitude": t_lat, "longitude": t_lon},
        "far_students": far,
        "threshold_km": threshold_km
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
