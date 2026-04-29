from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2, os, math
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from functools import wraps

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

app = Flask(__name__)
CORS(app)

teacher_positions = {}


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
        raise ValueError("ID number must be exactly 9 digits")
    return v


def parse_coords(coords):
    if not isinstance(coords, dict): raise ValueError("Invalid coordinates")
    def dms(obj, max_deg, axis):
        if not isinstance(obj, dict): raise ValueError(f"{axis} must be an object")
        d, m, s = int(str(obj.get("Degrees","")).strip()), int(str(obj.get("Minutes","")).strip()), int(str(obj.get("Seconds","")).strip())
        if not (0 <= d <= max_deg): raise ValueError(f"{axis} Degrees must be between 0 and {max_deg}")
        if not (0 <= m <= 59 and 0 <= s <= 59): raise ValueError(f"{axis} Minutes/Seconds must be between 0 and 59")
        return float(d) + m / 60 + s / 3600
    return dms(coords.get("Latitude"), 90, "Latitude"), dms(coords.get("Longitude"), 180, "Longitude")


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(math.sqrt(a))


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        tid = request.headers.get("X-Teacher-ID")
        if not tid or not query("SELECT 1 FROM teachers WHERE id_number=%s", (tid,), one=True):
            return jsonify({"error": "Access restricted to teachers only"}), 403
        return fn(*args, **kwargs)
    return wrapper


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict): raise ValueError("Invalid JSON")
    return data


def handle_insert_error(e):
    return (jsonify({"error": "ID number already registered"}), 409) if "23505" in str(e) else (jsonify({"error": str(e)}), 500)


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


# --- Teachers ---

@app.route("/api/teachers", methods=["POST"])
def register_teacher():
    data = request.get_json()
    for f in ["first_name", "last_name", "id_number", "class_name"]:
        if not str(data.get(f, "")).strip():
            return jsonify({"error": f"Missing field: {f}"}), 400
    try:
        id_num = validate_id(data["id_number"])
        insert("teachers", ["first_name","last_name","id_number","class_name"],
               (data["first_name"].strip(), data["last_name"].strip(), id_num, data["class_name"].strip()))
        return jsonify({"message": "Teacher registered successfully"}), 201
    except ValueError as e: return jsonify({"error": str(e)}), 400
    except Exception as e: return handle_insert_error(e)


@app.route("/api/teachers/<id_number>", methods=["GET"])
@auth_required
def get_teacher(id_number):
    r = query("SELECT first_name,last_name,id_number,class_name FROM teachers WHERE id_number=%s", (id_number,), one=True)
    return jsonify(person_row(r)) if r else (jsonify({"error": "Teacher not found"}), 404)


@app.route("/api/teachers/<id_number>/students", methods=["GET"])
@auth_required
def get_teacher_students(id_number):
    t = query("SELECT class_name FROM teachers WHERE id_number=%s", (id_number,), one=True)
    if not t: return jsonify({"error": "Teacher not found"}), 404
    rows = query("SELECT first_name,last_name,id_number,class_name FROM students WHERE class_name=%s ORDER BY last_name", (t[0],))
    return jsonify({"class": t[0], "students": [person_row(r) for r in rows]})


# --- Students ---

@app.route("/api/students", methods=["POST"])
@auth_required
def register_student():
    try: data = json_body()
    except ValueError as e: return jsonify({"error": str(e)}), 400

    t = query("SELECT class_name FROM teachers WHERE id_number=%s", (request.headers.get("X-Teacher-ID"),), one=True)
    if not t: return jsonify({"error": "Teacher not found"}), 404
    teacher_class = t[0]

    for f in ["first_name", "last_name", "id_number", "class_name"]:
        if not str(data.get(f, "")).strip():
            return jsonify({"error": f"Missing field: {f}"}), 400
    if str(data["class_name"]).strip() != teacher_class:
        return jsonify({"error": f"You can only register students to class {teacher_class}"}), 403
    try:
        id_num = validate_id(data["id_number"])
        insert("students", ["first_name","last_name","id_number","class_name"],
               (data["first_name"].strip(), data["last_name"].strip(), id_num, teacher_class))
        return jsonify({"message": "Student registered successfully"}), 201
    except ValueError as e: return jsonify({"error": str(e)}), 400
    except Exception as e: return handle_insert_error(e)


# --- Locations ---

@app.route("/api/location", methods=["POST"])
def receive_location():
    data = request.get_json(silent=True)
    if not isinstance(data, dict): return jsonify({"error": "Invalid JSON"}), 400
    try:
        sid = validate_id(str(data.get("ID", "")).strip().zfill(9))
        coords = data.get("Coordinates")
        if not isinstance(coords, dict): return jsonify({"error": "Missing Coordinates"}), 400
        t_lat, t_lon = parse_coords(coords)
        def to_dms(v):
            d = int(v); mf = (v - d) * 60; m = int(mf)
            return d, m, min(59, round((mf - m) * 60))
        lat_d, lat_m, lat_s = to_dms(t_lat)
        lon_d, lon_m, lon_s = to_dms(t_lon)
        ts = data.get("Time", "")
        if not isinstance(ts, str) or not ts.strip(): raise ValueError("Missing Time")
        datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
        if not query("SELECT 1 FROM students WHERE id_number=%s", (sid,), one=True):
            return jsonify({"error": "Student not found"}), 404
        insert("locations",
               ["student_id_number","lon_degrees","lon_minutes","lon_seconds","lat_degrees","lat_minutes","lat_seconds","recorded_at"],
               (sid, lon_d, lon_m, lon_s, lat_d, lat_m, lat_s, ts.strip()))
        return jsonify({"message": "Location saved"}), 201
    except ValueError as e: return jsonify({"error": str(e)}), 400


@app.route("/api/locations", methods=["GET"])
@auth_required
def get_latest_locations():
    return jsonify([loc_row(r) for r in query(LOCATION_QUERY.format(where=""))])


# --- Distance Check ---

@app.route("/api/location/teacher/position", methods=["POST"])
@auth_required
def update_teacher_position():
    try:
        data = json_body()
        t_lat, t_lon = parse_coords(data.get("Coordinates"))
        tid = request.headers.get("X-Teacher-ID")
        teacher_positions[tid] = {"latitude": t_lat, "longitude": t_lon, "updated_at": datetime.utcnow().isoformat() + "Z"}
        return jsonify({"message": "Teacher location updated", "teacher_location": teacher_positions[tid]}), 200
    except ValueError as e: return jsonify({"error": str(e)}), 400


@app.route("/api/location/teacher", methods=["POST"])
@auth_required
def check_distance():
    try: data = json_body()
    except ValueError as e: return jsonify({"error": str(e)}), 400

    tid = request.headers.get("X-Teacher-ID")
    t = query("SELECT class_name FROM teachers WHERE id_number=%s", (tid,), one=True)
    if not t: return jsonify({"error": "Teacher not found"}), 404

    try:
        threshold_km = float(data.get("threshold_km", 3.0))
        if threshold_km <= 0: return jsonify({"error": "threshold_km must be greater than 0"}), 400
    except (TypeError, ValueError): return jsonify({"error": "threshold_km must be a number"}), 400

    try:
        coords = data.get("Coordinates")
        if coords is not None:
            t_lat, t_lon = parse_coords(coords)
        else:
            last = teacher_positions.get(tid)
            if not last: return jsonify({"error": "No GPS position received yet for this teacher"}), 400
            t_lat, t_lon = last["latitude"], last["longitude"]
    except ValueError as e: return jsonify({"error": str(e)}), 400

    rows = query(LOCATION_QUERY.format(where="WHERE s.class_name = %s"), (t[0],))
    far = [{**loc_row(r), "distance_km": round(d, 2)}
           for r in rows
           if (d := haversine(t_lat, t_lon, float(r[7])+r[8]/60+r[9]/3600, float(r[4])+r[5]/60+r[6]/3600)) > threshold_km]

    return jsonify({"teacher_location": {"latitude": t_lat, "longitude": t_lon}, "far_students": far, "threshold_km": threshold_km}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
