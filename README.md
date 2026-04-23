# מערכת ניהול טיול שנתי 🎒

מערכת לניהול הטיול השנתי של בנות כיתה ו׳ בבית הספר "בנות משה".

## תיאור המערכת

המערכת כוללת שלושה שלבים:
- **שלב א׳** — רישום מורות ותלמידות + API מוגן
- **שלב ב׳** — מפת איכון בזמן אמת
- **שלב ג׳ (בונוס)** — התראה על תלמידות שהתרחקו מהמורה

---

## Stack טכנולוגי

| שכבה | טכנולוגיה |
|------|-----------|
| Backend | Python 3.12 + Flask |
| Database | PostgreSQL |
| Frontend | HTML + CSS + Vanilla JS |
| Map | Leaflet.js (OpenStreetMap) |

---

## תלויות חיצוניות והתקנה

### דרישות מוקדמות
- Python 3.12+
- PostgreSQL (מותקן ורץ)

### 1. שכפול הפרויקט
```bash
git clone https://github.com/<your-username>/hadasim-trip_manager.git
cd hadasim-trip_manager
```

### 2. יצירת סביבה וירטואלית והתקנת חבילות
```bash
cd server
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 3. הגדרת משתני סביבה
ערכי את הקובץ `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hadasim_trip
DB_USER=postgres
DB_PASSWORD=<הסיסמה שלך>
```

### 4. אתחול מסד הנתונים
```bash
python init_db.py
```
הפקודה יוצרת את ה-database ואת כל הטבלאות.

### 5. הפעלת השרת
```bash
python app.py
```
השרת עולה על: `http://localhost:5000`

### 6. פתיחת ה-Frontend
הפעילי שרת סטטי מתוך תיקיית `client`:
```bash
cd ..\client
python -m http.server 8080
```
ואז פתחי בדפדפן:
- `http://localhost:8080/index.html`
- `http://localhost:8080/map.html`

או פשוט:
פתחי את הקובץ `client/index.html` בדפדפן.

---

## API Endpoints

### מורות (Teachers)
| Method | Route | תיאור | Auth |
|--------|-------|-------|------|
| POST | `/api/teachers` | רישום מורה חדשה | לא נדרש |
| GET | `/api/teachers` | כל המורות | מורה |
| GET | `/api/teachers/<id>` | מורה ספציפית | מורה |
| GET | `/api/teachers/<id>/students` | תלמידות הכיתה | מורה |

### תלמידות (Students)
| Method | Route | תיאור | Auth |
|--------|-------|-------|------|
| POST | `/api/students` | רישום תלמידה | מורה |
| GET | `/api/students` | כל התלמידות | מורה |
| GET | `/api/students/<id>` | תלמידה ספציפית | מורה |

### מיקומים (Locations)
| Method | Route | תיאור | Auth |
|--------|-------|-------|------|
| POST | `/api/location` | שליחת מיקום ממכשיר | לא נדרש |
| GET | `/api/locations` | מיקום אחרון של כל תלמידה | מורה |
| POST | `/api/location/teacher/position` | עדכון GPS של מורה | מורה |
| POST | `/api/location/teacher` | בדיקת מרחק (שלב ג׳) | מורה |

**Auth:** כל בקשה מוגנת דורשת Header: `X-Teacher-ID: <תעודת זהות>`

---

## אופן השימוש

### שלב א׳ — רישום
1. פתחי `client/index.html`
2. לרישום **מורה** — מלאי שם, תעודת זהות וכיתה ולחצי "רישום מורה"
3. לרישום **תלמידה** — הזיני תעודת זהות של מורה בשורת האימות → "אמת" → עברי לטאב תלמידה

### שלב ב׳ — מפת איכון
1. פתחי `client/map.html`
2. אמתי מורה
3. המפה טוענת את כל המיקומים ומתרעננת כל 60 שניות

### שלב ג׳ — בדיקת מרחק
1. בדף המפה, מיקום המורה מתעדכן אוטומטית (GPS)
2. לחצי "בדוק מרחק"
3. המערכת מחשבת מרחק Haversine ומציגה תלמידות שהתרחקו מעל 3 ק"מ

---

## הנחות מקלות
1. **אימות פשוט**: מנגנון האבטחה מבוסס על Header `X-Teacher-ID` — לא מימשתי JWT/Session מלאים. הנחה: ה-API נגיש רק לממשק הפנימי.
2. **קואורדינטות DMS חיוביות**: הנחה שכל הקואורדינטות חיוביות (ישראל נמצאת ב-N/E).
3. **מיקום מורה**: מיקום המורה מתעדכן אוטומטית בסימולציה במסך המפה.
