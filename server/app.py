"""
app.py
------
נקודת הכניסה הראשית לשרת.
כאן יוצרים את אפליקציית Flask ומחברים אליה את כל ה-Blueprints (מודולי ה-routes).

הרצה:
    python app.py
    
השרת יעלה על: http://localhost:5000
"""

from flask import Flask
from flask_cors import CORS
from routes.teachers  import teachers_bp
from routes.students  import students_bp
from routes.locations import locations_bp

# יצירת אפליקציית Flask
app = Flask(__name__)

# CORS — מאפשר לדפדפן לשלוח בקשות מ-localhost לשרת שלנו.
# בלי זה, הדפדפן יחסום את הבקשות מהקוד שלנו!
CORS(app)

# חיבור ה-Blueprints לאפליקציה
# Blueprint = "קובוצת routes". מאפשר לנו לחלק את הקוד לקבצים נפרדים.
app.register_blueprint(teachers_bp)
app.register_blueprint(students_bp)
app.register_blueprint(locations_bp)


@app.route("/")
def health_check():
    """בדיקת חיות — אם מגיעים לכאן השרת עולה ועובד."""
    return {"status": "ok", "message": "מערכת ניהול הטיול פעילה ✅"}, 200


if __name__ == "__main__":
    # debug=True = שרת יתרענן אוטומטית כשמשנים קוד (נוח לפיתוח)
    app.run(debug=True, port=5000)
