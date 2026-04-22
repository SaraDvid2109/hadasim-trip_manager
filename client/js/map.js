/**
 * map.js
 * ------
 * לוגיקת המפה — שלב ב' ושלב ג'.
 * 
 * שלב ב': טוען מיקומים מה-API ומציג על מפת Leaflet, מתרענן כל 60 שניות.
 * שלב ג': שולח מיקום המורה ומציג תלמידות שהתרחקו יותר מ-3 ק"מ.
 */

const API_BASE = "http://localhost:5000";

// ── אתחול המפה ───────────────────────────────────────────────────────────────

/**
 * L.map("map") — יוצר מפת Leaflet בתוך ה-div עם id="map".
 * setView([lat, lon], zoom) — ממקם את מרכז המפה בירושלים עם zoom 13.
 */
const map = L.map("map").setView([31.7683, 35.2137], 13);  // ירושלים

/**
 * TileLayer = שכבת אריחים — התמונות שמרכיבות את המפה.
 * משתמשים ב-CartoDB (מבוסס על OpenStreetMap) — חינמי, לא חוסם file:// URLs.
 */
L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/">CARTO</a>',
  subdomains: "abcd",
  maxZoom: 19
}).addTo(map);

// אובייקט שישמור את ה-markers על המפה: { id_number: markerObject }
const markers = {};

// אובייקט לשמירת ה-teacher marker
let teacherMarker = null;


// ── Auth ─────────────────────────────────────────────────────────────────────

function setMapAuth() {
  const id = document.getElementById("mapTeacherId").value.trim();
  if (!/^\d{9}$/.test(id)) { alert("תעודת זהות חייבת להיות 9 ספרות"); return; }
  sessionStorage.setItem("teacherAuthId", id);
  const badge = document.getElementById("mapAuthBadge");
  badge.textContent = `✓ מאומתת: ${id}`;
  badge.className = "badge badge-auth";
  badge.style.display = "inline-flex";
  loadLocations();
}

function getTeacherAuthId() {
  return sessionStorage.getItem("teacherAuthId");
}


// ── טעינת מיקומים ────────────────────────────────────────────────────────────

/**
 * שולחת GET ל-/api/locations וממשיכה לעדכן את המפה.
 * 
 * הנקודות שמחזיר השרת כבר ב-Decimal Degrees (השרת עשה המרה מ-DMS).
 */
async function loadLocations() {
  const teacherId = getTeacherAuthId();
  if (!teacherId) {
    document.getElementById("lastUpdate").textContent = " נא לאמת מורה קודם";
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/locations`, {
      headers: { "X-Teacher-ID": teacherId }
    });

    if (!response.ok) {
      document.getElementById("lastUpdate").textContent = " שגיאה בטעינת נתונים";
      return;
    }

    const students = await response.json();
    updateMap(students);
    updateStudentList(students);

    const now = new Date().toLocaleTimeString("he-IL");
    document.getElementById("lastUpdate").textContent = ` עודכן בשעה ${now}`;

  } catch (err) {
    document.getElementById("lastUpdate").textContent = " שגיאת חיבור לשרת";
  }
}


// ── עדכון המפה ────────────────────────────────────────────────────────────────

/**
 * מעדכנת את ה-markers על המפה.
 * 
 * לכל תלמידה:
 * - אם ה-marker כבר קיים — מזיז אותו למיקום החדש
 * - אם לא קיים — יוצר marker חדש
 * 
 * @param {Array} students - רשימת תלמידות עם latitude, longitude
 */
function updateMap(students) {
  students.forEach(student => {
    const lat = student.latitude;
    const lon = student.longitude;
    const label = `${student.first_name} ${student.last_name}`;

    if (markers[student.id_number]) {
      // Marker קיים — מזיזים למיקום חדש
      markers[student.id_number].setLatLng([lat, lon]);
      markers[student.id_number].setPopupContent(buildPopupContent(student));
    } else {
      // Marker חדש — יוצרים ומוסיפים למפה
      const marker = L.marker([lat, lon], {
        // אייקון מותאם אישית — תיבה אדומה עם שם התלמידה (כמו בדוגמת ה-UI)
        icon: L.divIcon({
          className: "",
          html: `<div style="
            background: white;
            border: 2px solid #ef4444;
            border-radius: 6px;
            padding: 3px 8px;
            font-family: Heebo, sans-serif;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            direction: rtl;
          ">${label}</div>
          <div style="
            width: 0; height: 0;
            border-left: 8px solid transparent;
            border-right: 8px solid transparent;
            border-top: 10px solid #ef4444;
            margin: 0 auto;
          "></div>`,
          iconAnchor: [40, 40]
        })
      });

      marker.addTo(map);
      marker.bindPopup(buildPopupContent(student));
      markers[student.id_number] = marker;
    }
  });
}


/**
 * בונה את תוכן ה-Popup שמופיע בלחיצה על marker.
 */
function buildPopupContent(student) {
  return `
    <div style="direction:rtl; font-family:Heebo,sans-serif; min-width:160px">
      <strong>${student.first_name} ${student.last_name}</strong><br/>
      <small>כיתה: ${student.class_name}</small><br/>
      <small>ת.ז: ${student.id_number}</small><br/>
      <small>עדכון: ${new Date(student.recorded_at).toLocaleTimeString("he-IL")}</small>
    </div>
  `;
}


// ── עדכון רשימת התלמידות ─────────────────────────────────────────────────────

function updateStudentList(students) {
  const container = document.getElementById("studentList");

  if (students.length === 0) {
    container.innerHTML = "<p style='color:var(--muted)'>אין מיקומים זמינים</p>";
    return;
  }

  container.innerHTML = students.map(s => `
    <div class="student-card" onclick="flyToStudent('${s.id_number}')">
      <h4>${s.first_name} ${s.last_name}</h4>
      <div class="meta">כיתה: ${s.class_name} | ת.ז: ${s.id_number}</div>
      <div class="meta">
        📍 ${s.latitude.toFixed(4)}, ${s.longitude.toFixed(4)}
      </div>
      <div class="meta">🕐 ${new Date(s.recorded_at).toLocaleTimeString("he-IL")}</div>
    </div>
  `).join("");
}


/**
 * עפה למיקום תלמידה על המפה בלחיצה על הכרטיסייה שלה.
 */
function flyToStudent(idNumber) {
  const marker = markers[idNumber];
  if (marker) {
    map.flyTo(marker.getLatLng(), 16, { animate: true, duration: 1 });
    marker.openPopup();
  }
}


// ── שלב ג': בדיקת מרחק ──────────────────────────────────────────────────────

/**
 * שולחת מיקום המורה לשרת ומציגה תלמידות שהתרחקו.
 * השרת מחשב את המרחק בנוסחת Haversine ומחזיר רק מי שמרחקה > 3 ק"מ.
 */
async function checkDistance() {
  const teacherId = getTeacherAuthId();
  if (!teacherId) {
    showDistanceAlert("נא לאמת מורה קודם", "error");
    return;
  }

  // בניית ה-JSON בפורמט שהשרת מצפה לו (זהה לפורמט מכשיר האיכון)
  const payload = {
    ID: parseInt(teacherId),
    Coordinates: {
      Longitude: {
        Degrees: document.getElementById("tLonDeg").value,
        Minutes: document.getElementById("tLonMin").value,
        Seconds: document.getElementById("tLonSec").value
      },
      Latitude: {
        Degrees: document.getElementById("tLatDeg").value,
        Minutes: document.getElementById("tLatMin").value,
        Seconds: document.getElementById("tLatSec").value
      }
    },
    Time: new Date().toISOString()
  };

  // וולידציה בסיסית
  const vals = [payload.Coordinates.Longitude, payload.Coordinates.Latitude];
  for (const coord of vals) {
    if (!coord.Degrees || !coord.Minutes || !coord.Seconds) {
      showDistanceAlert("יש למלא את כל שדות הקואורדינטות", "error");
      return;
    }
  }

  try {
    const response = await fetch(`${API_BASE}/api/location/teacher`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Teacher-ID": teacherId
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (!response.ok) {
      showDistanceAlert(result.error || "שגיאה", "error");
      return;
    }

    // הצגת marker המורה על המפה
    const tLat = result.teacher_location.latitude;
    const tLon = result.teacher_location.longitude;
    showTeacherOnMap(tLat, tLon);

    // הצגת תוצאות
    displayFarStudents(result.far_students);

  } catch (err) {
    showDistanceAlert("שגיאת חיבור לשרת", "error");
  }
}


/**
 * מציגה marker של המורה על המפה.
 */
function showTeacherOnMap(lat, lon) {
  if (teacherMarker) {
    teacherMarker.setLatLng([lat, lon]);
  } else {
    teacherMarker = L.marker([lat, lon], {
      icon: L.divIcon({
        className: "",
        html: `<div style="
          background: #4f46e5;
          color: white;
          border-radius: 6px;
          padding: 3px 8px;
          font-family: Heebo, sans-serif;
          font-size: 12px;
          font-weight: 700;
          white-space: nowrap;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        ">👩‍🏫 מורה</div>
        <div style="
          width: 0; height: 0;
          border-left: 8px solid transparent;
          border-right: 8px solid transparent;
          border-top: 10px solid #4f46e5;
          margin: 0 auto;
        "></div>`,
        iconAnchor: [30, 40]
      })
    }).addTo(map);
  }
  map.flyTo([lat, lon], 13);
}


/**
 * מציגה את רשימת התלמידות שהתרחקו.
 */
function displayFarStudents(farStudents) {
  const container = document.getElementById("farStudentsContainer");
  const list = document.getElementById("farStudentsList");

  if (farStudents.length === 0) {
    showDistanceAlert("✅ כל התלמידות נמצאות בטווח של 3 ק\"מ ממך", "success");
    container.style.display = "none";
    return;
  }

  showDistanceAlert(`⚠️ נמצאו ${farStudents.length} תלמידות שהתרחקו!`, "error");

  // הדגשת ה-marker שלהן על המפה
  farStudents.forEach(s => {
    if (markers[s.id_number]) {
      markers[s.id_number].getElement()
        ?.querySelector("div")
        ?.style.setProperty("border-color", "#f59e0b");
    }
  });

  list.innerHTML = farStudents.map(s => `
    <div class="student-card far-alert" onclick="flyToStudent('${s.id_number}')">
      <h4>⚠️ ${s.first_name} ${s.last_name}</h4>
      <div class="meta">כיתה: ${s.class_name}</div>
      <span class="distance-badge">${s.distance_km} ק"מ ממך</span>
    </div>
  `).join("");

  container.style.display = "block";
}


function showDistanceAlert(msg, type) {
  const el = document.getElementById("distanceAlert");
  el.textContent = msg;
  el.className = `alert alert-${type} show`;
  setTimeout(() => { el.className = "alert"; }, 5000);
}


// ── עדכון אוטומטי כל 60 שניות ────────────────────────────────────────────────
/**
 * setInterval = מריץ פונקציה כל X מילי-שניות.
 * 60000ms = 60 שניות.
 * כך המפה מתרעננת אוטומטית כשמגיעים עדכוני מיקום חדשים.
 */
setInterval(loadLocations, 60000);


// ── אתחול ─────────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const saved = getTeacherAuthId();
  if (saved) {
    document.getElementById("mapTeacherId").value = saved;
    const badge = document.getElementById("mapAuthBadge");
    badge.textContent = `✓ מאומתת: ${saved}`;
    badge.className = "badge badge-auth";
    badge.style.display = "inline-flex";
    loadLocations();  // טוען מיד אם כבר מאומתת
  }
});
