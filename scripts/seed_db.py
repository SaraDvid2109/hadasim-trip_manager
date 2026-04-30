import requests

SERVER_URL = "http://localhost:5000"

teachers = [
    {"first_name": "Sarah",  "last_name": "Levi",      "id_number": "310310310", "class_name": "6A"},
    {"first_name": "Miriam", "last_name": "Cohen",     "id_number": "420420420", "class_name": "6B"},
    {"first_name": "Rachel", "last_name": "Goldberg",  "id_number": "530530530", "class_name": "6C"},
]

students = [
    {"first_name": "Maya",    "last_name": "Abraham",  "id_number": "111111111", "class_name": "6A"},
    {"first_name": "Noa",     "last_name": "Ben David", "id_number": "111111112", "class_name": "6A"},
    {"first_name": "Tamar",   "last_name": "Green",    "id_number": "111111113", "class_name": "6A"},
    {"first_name": "Esther",  "last_name": "Dahan",    "id_number": "111111114", "class_name": "6A"},
    {"first_name": "Liat",    "last_name": "Halevi",   "id_number": "222222221", "class_name": "6B"},
    {"first_name": "Shira",   "last_name": "Weiss",    "id_number": "222222222", "class_name": "6B"},
    {"first_name": "Dana",    "last_name": "Zacharia",  "id_number": "222222223", "class_name": "6B"},
    {"first_name": "Orit",    "last_name": "Hazan",    "id_number": "222222224", "class_name": "6B"},
    {"first_name": "Yael",    "last_name": "Tal",      "id_number": "333333331", "class_name": "6C"},
    {"first_name": "Hadas",   "last_name": "Yitzhak",  "id_number": "333333332", "class_name": "6C"},
    {"first_name": "Rina",    "last_name": "Katz",     "id_number": "333333333", "class_name": "6C"},
    {"first_name": "Penina",  "last_name": "Levana",   "id_number": "333333334", "class_name": "6C"},
]

# Jerusalem area: Western Wall, Mount Scopus, Old City
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

# POST request function
def post_request(endpoint, data, headers=None):
    url = f"{SERVER_URL}{endpoint}"
    try:
        response = requests.post(url, json=data, headers=headers)
        return response.status_code, response.json()
    except Exception as e:
        return 500, {"error": str(e)}

# --- Helper functions ---
def dms(t): 
    return {"Degrees": str(t[0]), "Minutes": str(t[1]), "Seconds": str(t[2])}

def log(status, r): 
    print(f"  {status}: {r.get('message') or r.get('error')}")

if __name__ == "__main__":

    print("=== Registering teachers ===")
    for t in teachers: 
        log(*post_request("/api/teachers", t))

    print("\n=== Registering students ===")
    for s in students:
        teacher_id = next(t["id_number"] for t in teachers if t["class_name"] == s["class_name"])
        log(*post_request("/api/students", s, {"X-Teacher-ID": teacher_id}))

    print("\n=== Sending locations ===")
    for sid, lat, lon, t in locations:
        log(*post_request("/api/location", {"ID": sid, "Coordinates": {"Longitude": dms(lon), "Latitude": dms(lat)}, "Time": t}))

    print(f"\n[DONE]")
