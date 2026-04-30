# Trip Manager

A school trip management system for tracking students in real time.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Setup](#setup)
- [Usage](#usage)
- [Access Control](#access-control)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Stages](#stages)
- [Assumptions](#assumptions)

---

## Tech Stack

| Layer    | Technology                       |
|----------|----------------------------------|
| Backend  | Python 3.12 + Flask              |
| Database | PostgreSQL                       |
| Frontend | HTML + CSS + Vanilla JS          |
| Map      | Leaflet.js                       |

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
venv\Scripts\activate      
pip install -r requirements.txt
```

### 3. Configure environment
Edit `.env` (project root):
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
server\venv\Scripts\python.exe scripts\seed_db.py
```
Seeds 3 teachers (classes 6A/6B/6C), 12 students (4 per class), and 12 location entries.  
Default teacher login IDs: 310310310 (6A), 420420420 (6B), 530530530 (6C)

### 7. Open the frontend
```bash
cd client
start http://localhost:8080/index.html && py -m http.server 8080
```

---

## Usage

### Login Screen
Enter your 9-digit teacher ID to sign in.

<!-- Screenshot: Login screen -->
<img width="1914" height="866" alt="image" src="https://github.com/user-attachments/assets/af94c1cc-3978-4189-b7ab-e99d5a9a2a88" />

### Stage A — Registration (index.html)
Register teachers and students. A teacher can only add students to their own class.

| Register Teacher | Register Student |
|-----------------|-----------------|
| <img width="1917" height="865" alt="image" src="https://github.com/user-attachments/assets/6def7f52-bacf-4cc4-9edc-0c93640eaeff" />| <img width="1918" height="874" alt="image" src="https://github.com/user-attachments/assets/7e9b72cb-727e-4db3-a657-fef111463077" />|

### Stage B — Live Map (map.html)
The map displays the latest reported location of every student in the teacher's class. It auto-refreshes every 60 seconds.

<!-- Screenshot: Map with student markers -->
<img width="1913" height="867" alt="image" src="https://github.com/user-attachments/assets/3de87dbf-3bba-4053-8a66-a3e665ddea40" />


### Stage C — Distance Check
Click the distance-check button on the map screen to highlight students who are farther than the configured threshold (default 3 km).

<!-- Screenshot: Distance check result with highlighted students -->
<img width="1915" height="869" alt="image" src="https://github.com/user-attachments/assets/0b5a4801-2c99-451f-b127-fd0e88e63fb1" />

---

## Access Control

**All pages require teacher login.** 
On first load, index.html shows a login screen.
Enter your 9-digit teacher ID - the system validates against the teachers table.
After login, the session is stored in sessionStorage and shared with map.html.
Navigating to map.html without a session redirects back to the login screen.

Sign Out clears the session on both pages.

Protected API endpoints require the header: `X-Teacher-ID: <id_number>`

---

## Database Schema

| Table      | Primary Key | Notes |
|------------|-------------|-------|
| teachers | id_number CHAR(9) | No surrogate key — ID number is the PK |
| students | id_number CHAR(9) | No surrogate key — ID number is the PK |
| locations | id SERIAL | Log table; kept surrogate PK as there is no natural PK |

A teacher can only register students into their own class (class_name must match).

Coordinates are stored in DMS format (degrees, minutes, seconds) as separate integer columns and converted to decimal degrees on read.

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
| POST | `/api/students` | Register a student (class-restricted) | Teacher |

### Locations
| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| POST | `/api/location` | Submit student location | No |
| GET | `/api/locations` | Latest location per student (all classes) | Teacher |
| POST | `/api/location/teacher/position` | Update teacher GPS (stored in memory) | Teacher |
| POST | `/api/location/teacher` | Distance check (Stage C) | Teacher |

#### `/api/location` - Request body
```json
{
  "ID": "123456789",
  "Coordinates": {
    "Latitude":  { "Degrees": "31", "Minutes": "46", "Seconds": "28" },
    "Longitude": { "Degrees": "35", "Minutes": "14", "Seconds": "3"  }
  },
  "Time": "2026-04-22T08:00:00Z"
}
```

#### `/api/location/teacher` - Request body
```json
{
  "threshold_km": 3.0,
  "Coordinates": {
    "Latitude":  { "Degrees": "31", "Minutes": "46", "Seconds": "0" },
    "Longitude": { "Degrees": "35", "Minutes": "14", "Seconds": "0" }
  }
}
```
`Coordinates` is optional - if omitted, the server uses the last position stored via `/api/location/teacher/position`.  
`threshold_km` defaults to `3.0` if not provided.

---

## Stages

- **Stage A**: Teacher & student registration via `index.html`
- **Stage B**: Real-time tracking map via `map.html` (auto-refreshes every 60s)
- **Stage C (Bonus)**: Haversine distance check, highlights students beyond a configurable threshold (default 3 km)

---

## Assumptions
1. **Auth**: Header-based (X-Teacher-ID) + sessionStorage - intended for internal use only.
2. **Coordinates**: All coordinates are positive (Israel is N/E).
3. **Teacher location**: Stored in server memory (teacher_positions dict), resets on server restart.
4. **Class restriction**: A teacher can only register students to their own class.
