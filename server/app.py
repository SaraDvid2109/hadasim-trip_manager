from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2, os, math
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

app = Flask(__name__)
CORS(app)

teacher_positions = {}  # מיקום אחרון של מורה בזיכרון


def db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def query(sql, params=(), one=False):
    conn = db(); cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone() if one else cur.fetchall()
    cur.close(); conn.close()
    return row


def insert(table, fields, values):
    conn = db(); cur = conn.cursor()
    ph = ",".join(["%s"] * len(values))
    try:
        cur.execute(f"INSERT INTO {table}({','.join(fields)}) VALUES({ph})", values)
        conn.commit()
    except Exception as e:
        conn.rollback(); raise e
    finally:
        cur.close(); conn.close()


def person_row(r):
    return {"first_name": r[0], "last_name": r[1], "id_number": r[2], "class_name": r[3]}


def validate_id(val):
    v = str(val).strip()
    if not v.isdigit() or len(v) != 9:
        raise ValueError("תעודת זהות חייבת להיות 9 ספרות")
    return v


def parse_dms(obj, max_deg, axis):
    if not isinstance(obj, dict): raise ValueError(f"{axis} חייב להיות אובייקט")
    d, m, s = int(str(obj.get("Degrees","")).strip()), int(str(obj.get("Minutes","")).strip()), int(str(obj.get("Seconds","")).strip())
    if not (0 <= d <= max_deg): raise ValueError(f"{axis} Degrees חייב להיות בין 0 ל-{max_deg}")
    if not (0 <= m <= 59 and 0 <= s <= 59): raise ValueError(f"{axis} Minutes/Seconds חייבים להיות בין 0 ל-59")
    return float(d) + m / 60 + s / 3600


def parse_coords(coords):
    if not isinstance(coords, dict): raise ValueError("Coordinates לא תקין")
    return parse_dms(coords.get("Latitude"), 90, "Latitude"), parse_dms(coords.get("Longitude"), 180, "Longitude")


def validate_time(ts):
    if not isinstance(ts, str) or not ts.strip(): raise ValueError("Time חסר")
    datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
    return ts.strip()


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(math.sqrt(a))


def get_tid():
    return request.headers.get("X-Teacher-ID")


def auth_required(fn):
    def wrapper(*args, **kwargs):
        tid = get_tid()
        if not tid or not query("SELECT 1 FROM teachers WHERE id_number=%s", (tid,), one=True):
            return jsonify({"error": "גישה מותרת למורות בלבד"}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict): raise ValueError("JSON לא תקין")
    return data


def handle_insert_error(e):
    return (jsonify({"error": "תעודת זהות כבר רשומה"}), 409) if "23505" in str(e) else (jsonify({"error": str(e)}), 500)


LOCATION_QUERY = """
    SELECT DISTINCT ON (l.student_id_number)
        l.student_id_number, s.first_name, s.last_name, s.class_name,
        l.lon_degrees, l.lon_minutes, l.lon_seconds,
        l.lat_degrees, l.lat_minutes, l.lat_seconds, l.recorded_at
    FROM locations l JOIN students s ON s.id_number = l.student_id_number
    {where}
    ORDER BY l.student_id_number, l.recorded_at DESC
"""

def loc_row(r):
    return {
        "id_number": r[0], "first_name": r[1], "last_name": r[2], "class_name": r[3],
        "longitude": float(r[4]) + r[5]/60 + r[6]/3600,
        "latitude":  float(r[7]) + r[8]/60 + r[9]/3600,
        "recorded_at": (r[10].isoformat() + "+00:00") if r[10] else None
    }


@app.route("/")
def health():
    return {"status": "ok"}, 200


# --- מורות ---

@app.route("/api/teachers", methods=["POST"])
def register_teacher():
    data = request.get_json()
    for f in ["first_name", "last_name", "id_number", "class_name"]:
        if not str(data.get(f, "")).strip():
            return jsonify({"error": f"שדה חסר: {f}"}), 400
    try:
        id_num = validate_id(data["id_number"])
        insert("teachers", ["first_name","last_name","id_number","class_name"],
               (data["first_name"].strip(), data["last_name"].strip(), id_num, data["class_name"].strip()))
        return jsonify({"message": "המורה נרשמה בהצלחה"}), 201
    except ValueError as e: return jsonify({"error": str(e)}), 400
    except Exception as e: return handle_insert_error(e)


@app.route("/api/teachers", methods=["GET"])
@auth_required
def get_all_teachers():
    return jsonify([person_row(r) for r in query("SELECT first_name,last_name,id_number,class_name FROM teachers ORDER BY last_name")])


@app.route("/api/teachers/<id_number>", methods=["GET"])
@auth_required
def get_teacher(id_number):
    r = query("SELECT first_name,last_name,id_number,class_name FROM teachers WHERE id_number=%s", (id_number,), one=True)
    return jsonify(person_row(r)) if r else (jsonify({"error": "מורה לא נמצאה"}), 404)


@app.route("/api/teachers/<id_number>/students", methods=["GET"])
@auth_required
def get_teacher_students(id_number):
    t = query("SELECT class_name FROM teachers WHERE id_number=%s", (id_number,), one=True)
    if not t: return jsonify({"error": "מורה לא נמצאה"}), 404
    rows = query("SELECT first_name,last_name,id_number,class_name FROM students WHERE class_name=%s ORDER BY last_name", (t[0],))
    return jsonify({"class": t[0], "students": [person_row(r) for r in rows]})


# --- תלמידות ---

@app.route("/api/students", methods=["POST"])
@auth_required
def register_student():
    try: data = json_body()
    except ValueError as e: return jsonify({"error": str(e)}), 400

    t = query("SELECT class_name FROM teachers WHERE id_number=%s", (get_tid(),), one=True)
    if not t: return jsonify({"error": "מורה לא נמצאה"}), 404
    teacher_class = t[0]

    for f in ["first_name", "last_name", "id_number", "class_name"]:
        if not str(data.get(f, "")).strip():
            return jsonify({"error": f"שדה חסר: {f}"}), 400
    if str(data["class_name"]).strip() != teacher_class:
        return jsonify({"error": f"ניתן לרשום תלמידה רק לכיתה {teacher_class}"}), 403
    try:
        id_num = validate_id(data["id_number"])
        insert("students", ["first_name","last_name","id_number","class_name"],
               (data["first_name"].strip(), data["last_name"].strip(), id_num, teacher_class))
        return jsonify({"message": "התלמידה נרשמה בהצלחה"}), 201
    except ValueError as e: return jsonify({"error": str(e)}), 400
    except Exception as e: return handle_insert_error(e)


@app.route("/api/students", methods=["GET"])
@auth_required
def get_all_students():
    return jsonify([person_row(r) for r in query("SELECT first_name,last_name,id_number,class_name FROM students ORDER BY class_name,last_name")])


@app.route("/api/students/<id_number>", methods=["GET"])
@auth_required
def get_student(id_number):
    r = query("SELECT first_name,last_name,id_number,class_name FROM students WHERE id_number=%s", (id_number,), one=True)
    return jsonify(person_row(r)) if r else (jsonify({"error": "תלמידה לא נמצאה"}), 404)


# --- מיקומים ---

@app.route("/api/location", methods=["POST"])
def receive_location():
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return jsonify({"error": "JSON לא תקין"}), 400
    try:
        sid = validate_id(str(data.get("ID", "")).strip().zfill(9))
        coords = data.get("Coordinates")
        if not isinstance(coords, dict): return jsonify({"error": "Coordinates חסר"}), 400
        t_lat, t_lon = parse_coords(coords)
        # המרה חזרה ל-DMS לשמירה בטבלה
        def to_dms(v):
            d = int(v); m_f = (v - d) * 60; m = int(m_f); s = min(59, round((m_f - m) * 60))
            return d, m, s
        lat_d, lat_m, lat_s = to_dms(t_lat)
        lon_d, lon_m, lon_s = to_dms(t_lon)
        t = validate_time(data.get("Time"))
        if not query("SELECT 1 FROM students WHERE id_number=%s", (sid,), one=True):
            return jsonify({"error": "תלמידה לא נמצאה"}), 404
        insert("locations",
               ["student_id_number","lon_degrees","lon_minutes","lon_seconds","lat_degrees","lat_minutes","lat_seconds","recorded_at"],
               (sid, lon_d, lon_m, lon_s, lat_d, lat_m, lat_s, t))
        return jsonify({"message": "מיקום נשמר"}), 201
    except ValueError as e: return jsonify({"error": str(e)}), 400


@app.route("/api/locations", methods=["GET"])
@auth_required
def get_latest_locations():
    return jsonify([loc_row(r) for r in query(LOCATION_QUERY.format(where=""))])


# --- שלב ג': בדיקת מרחק ---

@app.route("/api/location/teacher/position", methods=["POST"])
@auth_required
def update_teacher_position():
    try:
        data = json_body()
        coords = data.get("Coordinates")
        t_lat, t_lon = parse_coords(coords)
        teacher_positions[get_tid()] = {"latitude": t_lat, "longitude": t_lon, "updated_at": datetime.utcnow().isoformat() + "Z"}
        return jsonify({"message": "מיקום מורה נשמר", "teacher_location": teacher_positions[get_tid()]}), 200
    except ValueError as e: return jsonify({"error": str(e)}), 400


@app.route("/api/location/teacher", methods=["POST"])
@auth_required
def check_distance():
    try: data = json_body()
    except ValueError as e: return jsonify({"error": str(e)}), 400

    tid = get_tid()
    t = query("SELECT class_name FROM teachers WHERE id_number=%s", (tid,), one=True)
    if not t: return jsonify({"error": "מורה לא נמצאה"}), 404

    try:
        threshold_km = float(data.get("threshold_km", 3.0))
        if threshold_km <= 0: return jsonify({"error": "threshold_km חייב להיות גדול מ-0"}), 400
    except (TypeError, ValueError): return jsonify({"error": "threshold_km חייב להיות מספר"}), 400

    try:
        coords = data.get("Coordinates")
        if coords is not None:
            t_lat, t_lon = parse_coords(coords)
        else:
            last = teacher_positions.get(tid)
            if not last: return jsonify({"error": "לא התקבל עדיין מיקום GPS למורה"}), 400
            t_lat, t_lon = last["latitude"], last["longitude"]
    except ValueError as e: return jsonify({"error": str(e)}), 400

    rows = query(LOCATION_QUERY.format(where="WHERE s.class_name = %s"), (t[0],))
    far = [{**loc_row(r), "distance_km": round(d, 2)}
           for r in rows
           if (d := haversine(t_lat, t_lon, float(r[7])+r[8]/60+r[9]/3600, float(r[4])+r[5]/60+r[6]/3600)) > threshold_km]

    return jsonify({"teacher_location": {"latitude": t_lat, "longitude": t_lon}, "far_students": far, "threshold_km": threshold_km}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
