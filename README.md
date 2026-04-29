# Trip Manager

A school trip management system for tracking students in real time.

## Tech Stack

| Layer    | Technology                       |
|----------|----------------------------------|
| Backend  | Python 3.12 + Flask              |
| Database | PostgreSQL                       |
| Frontend | HTML + CSS + Vanilla JS          |
| Map      | Leaflet.js (OpenStreetMap/CARTO) |

---

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (running)

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/hadasim-trip_manager.git
cd hadasim-trip_manager
```

### 2. Create virtual environment & install dependencies
```bash
cd server
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 3. Configure environment
Edit `server/.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hadasim_trip
DB_USER=postgres
DB_PASSWORD=<your-password>
```

### 4. Initialize the database
Creates the `hadasim_trip` database (if it doesn't exist) and all tables:
```bash
server\venv\Scripts\python.exe scripts\init_db.py
```

> **Resetting the DB:** Drop existing tables in psql first, then re-run:
> ```sql
> DROP TABLE IF EXISTS locations;
> DROP TABLE IF EXISTS students;
> DROP TABLE IF EXISTS teachers;
> ```

### 5. Start the server
```bash
cd server
venv\Scripts\activate
python app.py
```
Server runs at `http://localhost:5000`

### 6. (Optional) Seed sample data
With the server running, in a separate terminal:
```bash
server\venv\Scripts\python.exe scripts\seed_data.py
```
Seeds 3 teachers (classes 6A/6B/6C), 12 students, and 12 locations.  
Default teacher login ID: **310310310**

### 7. Open the frontend
```bash
cd client
python -m http.server 8080
```
Open `http://localhost:8080/index.html` in your browser.

---

## Access Control

**All pages require teacher login.** On first load, `index.html` shows a login screen.
Enter your 9-digit teacher ID — the system validates against the `teachers` table.
After login, the session is stored in `sessionStorage` and shared with `map.html`.
Navigating to `map.html` without a session redirects back to the login screen.

Sign Out clears the session on both pages.

Protected API endpoints require the header: `X-Teacher-ID: <id_number>`

---

## Database Schema

| Table      | Primary Key | Notes |
|------------|-------------|-------|
| `teachers` | `id_number CHAR(9)` | No surrogate key — ID number is the PK |
| `students`  | `id_number CHAR(9)` | No surrogate key — ID number is the PK |
| `locations` | `id SERIAL` | Log table; kept surrogate PK as there is no natural PK |

A teacher can only register students into their own class (`class_name` must match).

---

## API Endpoints

### Teachers
| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| POST | `/api/teachers` | Register a teacher | No |
| GET | `/api/teachers/<id>` | Get teacher info | Teacher |
| GET | `/api/teachers/<id>/students` | Get class students | Teacher |

### Students
| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| POST | `/api/students` | Register a student | Teacher |

### Locations
| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| POST | `/api/location` | Submit student location | No |
| GET | `/api/locations` | Latest location per student | Teacher |
| POST | `/api/location/teacher/position` | Update teacher GPS | Teacher |
| POST | `/api/location/teacher` | Distance check (Stage C) | Teacher |

---

## Stages

- **Stage A** — Teacher & student registration via `index.html`
- **Stage B** — Real-time tracking map via `map.html` (auto-refreshes every 60s)
- **Stage C (Bonus)** — Haversine distance check; highlights students beyond the threshold

---

## Assumptions
1. **Auth**: Header-based (`X-Teacher-ID`) + `sessionStorage` — intended for internal use only.
2. **Coordinates**: All coordinates are positive (Israel is N/E).
3. **Teacher location**: Simulated automatically on the map screen.
4. **Class restriction**: A teacher can only register students to their own class.
