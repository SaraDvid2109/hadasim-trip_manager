"""
seed_data.py
------------
מאכלס את המסד בנתוני דוגמה:
- 3 מורות
- 12 תלמידות (4 לכל כיתה)
- מיקומים על המפה באזור ירושלים
"""

import urllib.request
import json
import sys
import io

# תיקון encoding לWindows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:5000"

def post(path, body, headers={}):
    data = json.dumps(body).encode("utf-8")
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read()), res.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

# ── מורות ─────────────────────────────────────────────────────────────────────
teachers = [
    {"first_name": "שרה",    "last_name": "לוי",    "id_number": "310310310", "class_name": "ו1"},
    {"first_name": "מרים",   "last_name": "כהן",    "id_number": "420420420", "class_name": "ו2"},
    {"first_name": "רחל",    "last_name": "גולדברג", "id_number": "530530530", "class_name": "ו3"},
]

print("=== רושמת מורות ===")
for t in teachers:
    res, status = post("/api/teachers", t)
    msg = res.get("message") or res.get("error")
    print(f"  {t['first_name']} {t['last_name']} [{t['id_number']}] → {status}: {msg}")

# ── תלמידות ───────────────────────────────────────────────────────────────────
students = [
    # כיתה ו1
    {"first_name": "מיכל",   "last_name": "אברהם",  "id_number": "111111111", "class_name": "ו1"},
    {"first_name": "נועה",   "last_name": "בן דוד", "id_number": "111111112", "class_name": "ו1"},
    {"first_name": "תמר",    "last_name": "גרין",   "id_number": "111111113", "class_name": "ו1"},
    {"first_name": "אסתר",   "last_name": "דהן",    "id_number": "111111114", "class_name": "ו1"},
    # כיתה ו2
    {"first_name": "ליאת",   "last_name": "הלוי",   "id_number": "222222221", "class_name": "ו2"},
    {"first_name": "שירה",   "last_name": "וייס",   "id_number": "222222222", "class_name": "ו2"},
    {"first_name": "דנה",    "last_name": "זכריה",  "id_number": "222222223", "class_name": "ו2"},
    {"first_name": "אורית",  "last_name": "חזן",    "id_number": "222222224", "class_name": "ו2"},
    # כיתה ו3
    {"first_name": "יעל",    "last_name": "טל",     "id_number": "333333331", "class_name": "ו3"},
    {"first_name": "הדס",    "last_name": "יצחק",   "id_number": "333333332", "class_name": "ו3"},
    {"first_name": "רינה",   "last_name": "כץ",     "id_number": "333333333", "class_name": "ו3"},
    {"first_name": "פנינה",  "last_name": "לבנה",   "id_number": "333333334", "class_name": "ו3"},
]

# משתמשים בת.ז של המורה הראשונה לאימות
AUTH_TEACHER = "310310310"

print("\n=== רושמת תלמידות ===")
for s in students:
    res, status = post("/api/students", s, {"X-Teacher-ID": AUTH_TEACHER})
    msg = res.get("message") or res.get("error")
    print(f"  {s['first_name']} {s['last_name']} [{s['id_number']}] → {status}: {msg}")

# ── מיקומים — כל התלמידות נמצאות באזור ירושלים ─────────────────────────────
# קואורדינטות DMS של אתרים בירושלים
locations = [
    # כיתה ו1 — אזור הכותל המערבי
    {"ID": 111111111, "lat": (31,46,28), "lon": (35,14,3),  "t": "2026-04-22T08:00:00Z"},
    {"ID": 111111112, "lat": (31,46,32), "lon": (35,14,8),  "t": "2026-04-22T08:01:00Z"},
    {"ID": 111111113, "lat": (31,46,25), "lon": (35,13,58), "t": "2026-04-22T08:02:00Z"},
    {"ID": 111111114, "lat": (31,46,35), "lon": (35,14,12), "t": "2026-04-22T08:03:00Z"},
    # כיתה ו2 — אזור הר הצופים
    {"ID": 222222221, "lat": (31,47,20), "lon": (35,14,50), "t": "2026-04-22T08:04:00Z"},
    {"ID": 222222222, "lat": (31,47,25), "lon": (35,14,55), "t": "2026-04-22T08:05:00Z"},
    {"ID": 222222223, "lat": (31,47,15), "lon": (35,14,45), "t": "2026-04-22T08:06:00Z"},
    {"ID": 222222224, "lat": (31,47,30), "lon": (35,15,0),  "t": "2026-04-22T08:07:00Z"},
    # כיתה ו3 — אזור העיר העתיקה
    {"ID": 333333331, "lat": (31,46,48), "lon": (35,13,48), "t": "2026-04-22T08:08:00Z"},
    {"ID": 333333332, "lat": (31,46,52), "lon": (35,13,52), "t": "2026-04-22T08:09:00Z"},
    {"ID": 333333333, "lat": (31,46,44), "lon": (35,13,44), "t": "2026-04-22T08:10:00Z"},
    {"ID": 333333334, "lat": (31,46,56), "lon": (35,13,56), "t": "2026-04-22T08:11:00Z"},
]

print("\n=== שולחת מיקומים ===")
for loc in locations:
    body = {
        "ID": loc["ID"],
        "Coordinates": {
            "Longitude": {"Degrees": str(loc["lon"][0]), "Minutes": str(loc["lon"][1]), "Seconds": str(loc["lon"][2])},
            "Latitude":  {"Degrees": str(loc["lat"][0]), "Minutes": str(loc["lat"][1]), "Seconds": str(loc["lat"][2])}
        },
        "Time": loc["t"]
    }
    res, status = post("/api/location", body)
    msg = res.get("message") or res.get("error")
    print(f"  ID {loc['ID']} → {status}: {msg}")

print("\n[DONE] הזנת נתונים הושלמה!")
print(f"  פתחי: http://localhost:8080/map.html")
print(f"  אמתי עם ת.ז מורה: {AUTH_TEACHER}")
