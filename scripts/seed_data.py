import urllib.request, json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:5000"
AUTH = "310310310"

def post(path, body, headers={}):
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", json.dumps(body).encode(), headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r: return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e: return json.loads(e.read()), e.code

def dms(t): return {"Degrees": str(t[0]), "Minutes": str(t[1]), "Seconds": str(t[2])}
def log(r, status): print(f"  {status}: {r.get('message') or r.get('error')}")

teachers = [
    {"first_name": "שרה",  "last_name": "לוי",     "id_number": "310310310", "class_name": "ו1"},
    {"first_name": "מרים", "last_name": "כהן",     "id_number": "420420420", "class_name": "ו2"},
    {"first_name": "רחל",  "last_name": "גולדברג", "id_number": "530530530", "class_name": "ו3"},
]

students = [
    {"first_name": "מיכל",  "last_name": "אברהם",  "id_number": "111111111", "class_name": "ו1"},
    {"first_name": "נועה",  "last_name": "בן דוד", "id_number": "111111112", "class_name": "ו1"},
    {"first_name": "תמר",   "last_name": "גרין",   "id_number": "111111113", "class_name": "ו1"},
    {"first_name": "אסתר",  "last_name": "דהן",    "id_number": "111111114", "class_name": "ו1"},
    {"first_name": "ליאת",  "last_name": "הלוי",   "id_number": "222222221", "class_name": "ו2"},
    {"first_name": "שירה",  "last_name": "וייס",   "id_number": "222222222", "class_name": "ו2"},
    {"first_name": "דנה",   "last_name": "זכריה",  "id_number": "222222223", "class_name": "ו2"},
    {"first_name": "אורית", "last_name": "חזן",    "id_number": "222222224", "class_name": "ו2"},
    {"first_name": "יעל",   "last_name": "טל",     "id_number": "333333331", "class_name": "ו3"},
    {"first_name": "הדס",   "last_name": "יצחק",   "id_number": "333333332", "class_name": "ו3"},
    {"first_name": "רינה",  "last_name": "כץ",     "id_number": "333333333", "class_name": "ו3"},
    {"first_name": "פנינה", "last_name": "לבנה",   "id_number": "333333334", "class_name": "ו3"},
]

# אזורי ירושלים: כותל, הר הצופים, עיר עתיקה
locations = [
    (111111111, (31,46,28), (35,14,3),  "2026-04-22T08:00:00Z"),
    (111111112, (31,46,32), (35,14,8),  "2026-04-22T08:01:00Z"),
    (111111113, (31,46,25), (35,13,58), "2026-04-22T08:02:00Z"),
    (111111114, (31,46,35), (35,14,12), "2026-04-22T08:03:00Z"),
    (222222221, (31,47,20), (35,14,50), "2026-04-22T08:04:00Z"),
    (222222222, (31,47,25), (35,14,55), "2026-04-22T08:05:00Z"),
    (222222223, (31,47,15), (35,14,45), "2026-04-22T08:06:00Z"),
    (222222224, (31,47,30), (35,15,0),  "2026-04-22T08:07:00Z"),
    (333333331, (31,46,48), (35,13,48), "2026-04-22T08:08:00Z"),
    (333333332, (31,46,52), (35,13,52), "2026-04-22T08:09:00Z"),
    (333333333, (31,46,44), (35,13,44), "2026-04-22T08:10:00Z"),
    (333333334, (31,46,56), (35,13,56), "2026-04-22T08:11:00Z"),
]

print("=== רושמת מורות ===")
for t in teachers: log(*post("/api/teachers", t))

print("\n=== רושמת תלמידות ===")
for s in students: log(*post("/api/students", s, {"X-Teacher-ID": AUTH}))

print("\n=== שולחת מיקומים ===")
for sid, lat, lon, t in locations:
    log(*post("/api/location", {"ID": sid, "Coordinates": {"Longitude": dms(lon), "Latitude": dms(lat)}, "Time": t}))

print(f"\n[DONE]  מפה: http://localhost:8080/map.html  |  ת.ז מורה: {AUTH}")
