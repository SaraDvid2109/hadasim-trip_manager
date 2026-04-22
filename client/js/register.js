/**
 * register.js
 * -----------
 * לוגיקת ה-JavaScript לדף הרישום.
 * 
 * אחראי על:
 * 1. ניהול ה-Tabs (עבור בין טפסים)
 * 2. אימות מורה — שמירת ה-ID ב-sessionStorage
 * 3. שליחת טפסי רישום ל-API
 */

const API_BASE = "http://localhost:5000";  // כתובת ה-backend שלנו

// ── ניהול Auth ────────────────────────────────────────────────────────────────

/**
 * שומרת את תעודת הזהות של המורה ב-sessionStorage.
 * sessionStorage = זיכרון שנמחק כשסוגרים את הכרטיסייה (בטוח יותר מ-localStorage).
 */
function setTeacherAuth() {
  const id = document.getElementById("teacherAuthId").value.trim();

  if (!/^\d{9}$/.test(id)) {
    alert("תעודת זהות חייבת להיות 9 ספרות");
    return;
  }

  sessionStorage.setItem("teacherAuthId", id);

  const badge = document.getElementById("authBadge");
  badge.textContent = `✓ מאומתת: ${id}`;
  badge.className = "badge badge-auth";
  badge.style.display = "inline-flex";
}

/**
 * מחזירה את תעודת הזהות השמורה, או null אם לא מאומתת.
 */
function getTeacherAuthId() {
  return sessionStorage.getItem("teacherAuthId");
}


// ── ניהול Tabs ────────────────────────────────────────────────────────────────

/**
 * עוברת בין טופס מורה לטופס תלמידה.
 * @param {'teacher' | 'student'} type
 */
function switchTab(type) {
  document.getElementById("formTeacher").style.display = type === "teacher" ? "block" : "none";
  document.getElementById("formStudent").style.display = type === "student" ? "block" : "none";
  document.getElementById("tabTeacher").className = "tab-btn" + (type === "teacher" ? " active" : "");
  document.getElementById("tabStudent").className  = "tab-btn" + (type === "student" ? " active" : "");
}


// ── עזר: הצגת הודעות ────────────────────────────────────────────────────────

/**
 * מציגה הודעת הצלחה/שגיאה תחת הטופס.
 * @param {string} elementId - ה-id של div ה-alert
 * @param {string} message   - הטקסט להצגה
 * @param {'success'|'error'} type
 */
function showAlert(elementId, message, type) {
  const el = document.getElementById(elementId);
  el.textContent = message;
  el.className = `alert alert-${type} show`;

  // מסתירה אחרי 4 שניות
  setTimeout(() => { el.className = "alert"; }, 4000);
}


// ── שליחת טופס מורה ─────────────────────────────────────────────────────────

/**
 * נשלח כשמגישים את טופס המורה.
 * שולח POST ל-/api/teachers עם הנתונים.
 * 
 * שים לב: רישום מורה לא דורש אימות — כל אחד יכול לרשום מורה.
 */
async function submitTeacher(event) {
  event.preventDefault();  // מונע רענון הדף ה-default של הדפדפן

  const data = {
    first_name: document.getElementById("tFirstName").value.trim(),
    last_name:  document.getElementById("tLastName").value.trim(),
    id_number:  document.getElementById("tIdNumber").value.trim(),
    class_name: document.getElementById("tClassName").value.trim()
  };

  try {
    const response = await fetch(`${API_BASE}/api/teachers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (response.ok) {
      showAlert("teacherAlert", "✅ " + result.message, "success");
      document.getElementById("teacherForm").reset();
    } else {
      showAlert("teacherAlert", "❌ " + result.error, "error");
    }

  } catch (err) {
    showAlert("teacherAlert", "❌ שגיאת חיבור לשרת", "error");
  }
}


// ── שליחת טופס תלמידה ───────────────────────────────────────────────────────

/**
 * נשלח כשמגישים את טופס התלמידה.
 * שולח POST ל-/api/students עם header X-Teacher-ID.
 * 
 * שים לב: רישום תלמידה דורש אימות מורה (header X-Teacher-ID).
 */
async function submitStudent(event) {
  event.preventDefault();

  const teacherId = getTeacherAuthId();
  if (!teacherId) {
    showAlert("studentAlert", "❌ יש להזין תעודת זהות מורה בשורת האימות ולאמת קודם", "error");
    return;
  }

  const data = {
    first_name: document.getElementById("sFirstName").value.trim(),
    last_name:  document.getElementById("sLastName").value.trim(),
    id_number:  document.getElementById("sIdNumber").value.trim(),
    class_name: document.getElementById("sClassName").value.trim()
  };

  try {
    const response = await fetch(`${API_BASE}/api/students`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Teacher-ID": teacherId   // ← כאן שולחים את האימות!
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (response.ok) {
      showAlert("studentAlert", "✅ " + result.message, "success");
      document.getElementById("studentForm").reset();
    } else {
      showAlert("studentAlert", "❌ " + result.error, "error");
    }

  } catch (err) {
    showAlert("studentAlert", "❌ שגיאת חיבור לשרת", "error");
  }
}

// ── אתחול: שחזור badge אם כבר מאומתת ──────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const saved = getTeacherAuthId();
  if (saved) {
    document.getElementById("teacherAuthId").value = saved;
    const badge = document.getElementById("authBadge");
    badge.textContent = `✓ מאומתת: ${saved}`;
    badge.className = "badge badge-auth";
    badge.style.display = "inline-flex";
  }
});
