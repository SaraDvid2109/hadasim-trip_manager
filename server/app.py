"""
app.py — מערכת ניהול טיול שנתי
כל השרת בקובץ אחד: חיבור DB, routes מורות, תלמידות ומיקומים.
הרצה: python app.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2, os, math
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

app = Flask(__name__)
CORS(app)

# שמירה בזיכרון של המיקום האחרון למורה לפי ת.ז
teacher_positions = {}


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

def get_teacher_class(id_number):
    """מחזירה את כיתת המורה לפי ת.ז, או None אם לא קיימת."""
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT class_name FROM teachers WHERE id_number = %s", (id_number,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row[0] if row else None

def parse_dms_triplet(dms_obj, max_degrees, axis_name):
    """מפרקת ומוודאת ערכי DMS תקינים."""
    if not isinstance(dms_obj, dict):
        raise ValueError(f"{axis_name} חייב להיות אובייקט")
    d = int(str(dms_obj.get("Degrees", "")).strip())
    m = int(str(dms_obj.get("Minutes", "")).strip())
    s = int(str(dms_obj.get("Seconds", "")).strip())
    if d < 0 or d > max_degrees:
        raise ValueError(f"{axis_name} Degrees חייב להיות בין 0 ל-{max_degrees}")
    if m < 0 or m > 59 or s < 0 or s > 59:
        raise ValueError(f"{axis_name} Minutes/Seconds חייבים להיות בין 0 ל-59")
    return d, m, s

def validate_iso_utc(ts):
    """מוודאת שחותמת הזמן בפורמט ISO תקין (כולל Z/UTC)."""
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError("Time חסר או לא תקין")
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    datetime.fromisoformat(cleaned)
    return ts.strip()

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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "גוף הבקשה חייב להיות JSON תקין"}), 400

    conn = None
    cur = None
    try:
        sid = str(data.get("ID", "")).strip().zfill(9)
        if not sid.isdigit() or len(sid) != 9:
            return jsonify({"error": "ID חייב להיות 9 ספרות"}), 400

        coordinates = data.get("Coordinates")
        if not isinstance(coordinates, dict):
            return jsonify({"error": "Coordinates חסר או לא תקין"}), 400

        lon_d, lon_m, lon_s = parse_dms_triplet(coordinates.get("Longitude"), 180, "Longitude")
        lat_d, lat_m, lat_s = parse_dms_triplet(coordinates.get("Latitude"), 90, "Latitude")
        recorded_time = validate_iso_utc(data.get("Time"))

        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT 1 FROM students WHERE id_number=%s", (sid,))
        if not cur.fetchone():
            return jsonify({"error": "תלמידה לא נמצאה"}), 404
        cur.execute(
            "INSERT INTO locations(student_id_number,lon_degrees,lon_minutes,lon_seconds,lat_degrees,lat_minutes,lat_seconds,recorded_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (sid, lon_d, lon_m, lon_s, lat_d, lat_m, lat_s, recorded_time)
        )
        conn.commit()
        return jsonify({"message": "מיקום נשמר בהצלחה"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "גוף הבקשה חייב להיות JSON תקין"}), 400

    class_name = get_teacher_class(tid)
    if not class_name:
        return jsonify({"error": "מורה לא נמצאה"}), 404

    # סף המרחק — ניתן להגדרה על ידי הקורא; ברירת מחדל 3 ק"מ (דרישת התרגיל)
    try:
        threshold_km = float(data.get("threshold_km", 3.0))
        if threshold_km <= 0:
            return jsonify({"error": "threshold_km חייב להיות גדול מ-0"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "threshold_km חייב להיות מספר"}), 400

    # ברירת מחדל: משתמשים במיקום ה-GPS האחרון של המורה שנשלח לשרת.
    # לתאימות לאחור, אם נשלחו Coordinates בבקשה זו - נשתמש בהם.
    try:
        coordinates = data.get("Coordinates")
        if coordinates is not None:
            if not isinstance(coordinates, dict):
                return jsonify({"error": "Coordinates לא תקין"}), 400
            tlon = coordinates.get("Longitude")
            tlat = coordinates.get("Latitude")
            t_lon_d, t_lon_m, t_lon_s = parse_dms_triplet(tlon, 180, "Longitude")
            t_lat_d, t_lat_m, t_lat_s = parse_dms_triplet(tlat, 90, "Latitude")
            t_lat = dms_to_decimal(t_lat_d, t_lat_m, t_lat_s)
            t_lon = dms_to_decimal(t_lon_d, t_lon_m, t_lon_s)
        else:
            last = teacher_positions.get(tid)
            if not last:
                return jsonify({"error": "לא התקבל עדיין מיקום GPS למורה"}), 400
            t_lat = last["latitude"]
            t_lon = last["longitude"]
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (l.student_id_number)
            l.student_id_number, s.first_name, s.last_name, s.class_name,
            l.lon_degrees, l.lon_minutes, l.lon_seconds,
            l.lat_degrees, l.lat_minutes, l.lat_seconds, l.recorded_at
        FROM locations l
        JOIN students s ON s.id_number = l.student_id_number
        WHERE s.class_name = %s
        ORDER BY l.student_id_number, l.recorded_at DESC
    """, (class_name,))
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


@app.route("/api/location/teacher/position", methods=["POST"])
def update_teacher_position():
    """
    מקבלת עדכון מיקום GPS של מורה ושומרת את המיקום האחרון שלה בזיכרון.
    דורש Header: X-Teacher-ID.
    פורמט הקלט זהה לשליחת מיקום תלמידה (Coordinates ב-DMS).
    """
    tid = request.headers.get("X-Teacher-ID")
    if not tid or not verify_teacher(tid):
        return jsonify({"error": "גישה מותרת למורות בלבד"}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "גוף הבקשה חייב להיות JSON תקין"}), 400

    try:
        coordinates = data.get("Coordinates")
        if not isinstance(coordinates, dict):
            return jsonify({"error": "Coordinates חסר או לא תקין"}), 400

        lon = coordinates.get("Longitude")
        lat = coordinates.get("Latitude")
        lon_d, lon_m, lon_s = parse_dms_triplet(lon, 180, "Longitude")
        lat_d, lat_m, lat_s = parse_dms_triplet(lat, 90, "Latitude")

        teacher_positions[tid] = {
            "latitude": dms_to_decimal(lat_d, lat_m, lat_s),
            "longitude": dms_to_decimal(lon_d, lon_m, lon_s),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        return jsonify({
            "message": "מיקום מורה נשמר בהצלחה",
            "teacher_location": {
                "latitude": teacher_positions[tid]["latitude"],
                "longitude": teacher_positions[tid]["longitude"],
                "updated_at": teacher_positions[tid]["updated_at"],
            },
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
