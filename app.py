import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Replace with a secure, random key
DATABASE = "academy.db"

def get_db():
    """Get or create a DB connection for the current context."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close the DB connection after each request."""
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    """Create tables if not exist, and ensure at least one admin account."""
    with app.app_context():
        db = get_db()
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
            -- possible roles: 'admin', 'teacher', 'student'
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            semester TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
        );

        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            grade_value TEXT NOT NULL,
            FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
        );
        """)
        db.commit()

        # Ensure at least one default admin if none exists
        cursor = db.execute("SELECT * FROM users WHERE role = 'admin'")
        admin_exist = cursor.fetchone()
        if not admin_exist:
            # Create a default admin account
            # In production, you might want to set environment variables instead of hardcoding
            db.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", "admin123", "admin")
            )
            db.commit()


# -----------------------------
# HOMEPAGE & LOGOUT
# -----------------------------
@app.route("/")
def index():
    """
    Home page with quick links for Admin, Teacher, Student login.
    No public registration for teacher/student.
    """
    return render_template("index.html")

@app.route("/logout")
def logout():
    """Logs out any user."""
    session.clear()
    return redirect(url_for("index"))


# -----------------------------
# ADMIN: LOGIN & DASHBOARD
# -----------------------------
@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ? AND role = 'admin'",
            (username, password)
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin Credentials."

    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    """
    Admin dashboard. Access: role='admin'.
    """
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admin Only."
    return render_template("admin_dashboard.html")

# CREATE TEACHER / STUDENT BY ADMIN
@app.route("/admin/create_user", methods=["GET", "POST"])
def create_user():
    """
    Admin can create new teacher or student accounts.
    """
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admin Only."

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]  # 'teacher' or 'student'

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, role)
            )
            db.commit()
        except sqlite3.IntegrityError:
            return "Error: Username already exists."

        return redirect(url_for("admin_dashboard"))

    return render_template("create_user.html")

# MANAGE COURSES
@app.route("/admin/manage_courses", methods=["GET", "POST"])
def manage_courses():
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admin Only."

    db = get_db()

    if request.method == "POST":
        name = request.form["course_name"]
        semester = request.form["semester"]
        db.execute(
            "INSERT INTO courses (name, semester) VALUES (?, ?)",
            (name, semester)
        )
        db.commit()
        return redirect(url_for("manage_courses"))

    courses = db.execute("SELECT * FROM courses").fetchall()
    return render_template("manage_courses.html", courses=courses)

@app.route("/admin/delete_course/<int:course_id>", methods=["POST"])
def delete_course(course_id):
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admin Only."

    db = get_db()
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()
    return redirect(url_for("manage_courses"))

@app.route("/admin/edit_course/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admin Only."

    db = get_db()
    if request.method == "POST":
        course_name = request.form["course_name"]
        semester = request.form["semester"]
        db.execute(
            "UPDATE courses SET name = ?, semester = ? WHERE id = ?",
            (course_name, semester, course_id)
        )
        db.commit()
        return redirect(url_for("manage_courses"))
    else:
        course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        return render_template("enroll.html", course=course, is_edit=True)


# -----------------------------
# TEACHER: LOGIN & DASHBOARD
# -----------------------------
@app.route("/login/teacher", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ? AND role = 'teacher'",
            (username, password)
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("teacher_dashboard"))
        else:
            return "Invalid Teacher Credentials."

    return render_template("teacher_login.html")

@app.route("/teacher/dashboard")
def teacher_dashboard():
    """
    Teacher dashboard. Has link to manage course attendance.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."
    return render_template("teacher_dashboard.html")

@app.route("/teacher/manage_attendance")
def teacher_manage_attendance():
    """
    Lists all courses for the teacher to pick from and mark attendance.
    For simplicity, we assume teacher can mark attendance for any course.
    In a real system, courses might be assigned to specific teacher_ids.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    courses = db.execute("SELECT * FROM courses").fetchall()
    return render_template("courses.html", courses=courses, is_teacher=True)

@app.route("/teacher/course_attendance/<int:course_id>", methods=["GET"])
def course_attendance(course_id):
    """
    Page for teacher to mark attendance for all students in a given course.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    enrollments = db.execute("""
        SELECT e.id AS enrollment_id, u.username AS student_name
        FROM enrollments e
        JOIN users u ON e.user_id = u.id
        WHERE e.course_id = ?
    """, (course_id,)).fetchall()

    return render_template("course_attendance.html", course=course, enrollments=enrollments)

@app.route("/teacher/process_attendance/<int:course_id>", methods=["POST"])
def process_attendance(course_id):
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    date = request.form["attendance_date"]
    db = get_db()

    for key in request.form:
        if key.startswith("status_"):
            enrollment_id_str = key.split("_")[1]
            status = request.form[key]  # 'present' or 'absent'
            db.execute(
                "INSERT INTO attendance (enrollment_id, date, status) VALUES (?, ?, ?)",
                (enrollment_id_str, date, status)
            )
    db.commit()
    return redirect(url_for("teacher_dashboard"))

# -----------------------------
# TEACHER: View & Update Existing Attendance
# -----------------------------

@app.route("/teacher/all_attendance")
def teacher_all_attendance():
    """
    Lists all existing attendance records so the teacher can update any record.
    In a real system, you might filter by courses the teacher actually teaches.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    attendance_records = db.execute("""
        SELECT a.id AS attendance_id,
               a.date,
               a.status,
               c.name AS course_name,
               u.username AS student_name
          FROM attendance a
          JOIN enrollments e ON a.enrollment_id = e.id
          JOIN courses c     ON e.course_id = c.id
          JOIN users u      ON e.user_id = u.id
      ORDER BY a.date DESC
    """).fetchall()

    # Render a template (e.g., "teacher_all_attendance.html") showing these records
    # Each record could have a link to /teacher/update_attendance/<attendance_id>
    return render_template("teacher_all_attendance.html", attendance_records=attendance_records)


@app.route("/teacher/update_attendance/<int:attendance_id>", methods=["GET", "POST"])
def update_attendance(attendance_id):
    """
    Allows the teacher to change a specific attendance record’s status (present/absent).
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()

    if request.method == "POST":
        # Update the attendance status
        new_status = request.form["status"]  # e.g., 'present' or 'absent'
        db.execute("UPDATE attendance SET status = ? WHERE id = ?", (new_status, attendance_id))
        db.commit()
        return redirect(url_for("teacher_all_attendance"))
    else:
        # Retrieve the existing attendance record to pre-fill in a form
        record = db.execute("""
            SELECT a.id    AS attendance_id,
                   a.date,
                   a.status,
                   c.name  AS course_name,
                   u.username AS student_name
              FROM attendance a
              JOIN enrollments e ON a.enrollment_id = e.id
              JOIN courses c     ON e.course_id = c.id
              JOIN users u      ON e.user_id = u.id
             WHERE a.id = ?
        """, (attendance_id,)).fetchone()

        # Render a template (e.g., "teacher_update_attendance.html") that lets teacher pick new status
        return render_template("teacher_update_attendance.html", record=record)

# -----------------------------
# STUDENT: LOGIN & DASHBOARD
# -----------------------------
@app.route("/login/student", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ? AND role = 'student'",
            (username, password)
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("student_dashboard"))
        else:
            return "Invalid Student Credentials."

    return render_template("student_login.html")

@app.route("/student/dashboard")
def student_dashboard():
    """
    Student dashboard. They can view courses and enroll, or see their enrollments.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."
    return render_template("student_dashboard.html")

@app.route("/courses")
def courses():
    """
    Shows all courses. Students can click 'Enroll.'
    Teachers might see 'Mark Attendance' but we separated that into teacher_manage_attendance.
    """
    if "user_id" not in session:
        return redirect(url_for("index"))

    db = get_db()
    course_list = db.execute("SELECT * FROM courses").fetchall()
    # We'll pass is_teacher only if session role is teacher
    is_teacher = (session.get("role") == "teacher")
    return render_template("courses.html", courses=course_list, is_teacher=is_teacher)

@app.route("/enroll/<int:course_id>", methods=["GET", "POST"])
def enroll(course_id):
    """
    Student enroll in a course.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."

    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)",
            (session["user_id"], course_id)
        )
        db.commit()
        return redirect(url_for("my_enrollments"))

    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    return render_template("enroll.html", course=course, is_edit=False)

@app.route("/my_enrollments")
def my_enrollments():
    """
    Shows courses the student is enrolled in.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."

    db = get_db()
    enrollments = db.execute("""
        SELECT c.name AS course_name, c.semester
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.user_id = ?
    """, (session["user_id"],)).fetchall()
    return render_template("my_enrollments.html", enrollments=enrollments)

# -----------------------------
# STUDENT: View Personal Attendance
# -----------------------------

@app.route("/student/my_attendance")
def my_attendance():
    """
    Shows the logged-in student all of their attendance records for all enrolled courses.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."

    db = get_db()
    attendance_list = db.execute("""
        SELECT a.date,
               a.status,
               c.name AS course_name
          FROM attendance a
          JOIN enrollments e ON a.enrollment_id = e.id
          JOIN courses c     ON e.course_id = c.id
         WHERE e.user_id = ?
      ORDER BY a.date DESC
    """, (session["user_id"],)).fetchall()

    # Render a template (e.g., "student_view_attendance.html") to list these records
    return render_template("student_view_attendance.html", attendance_list=attendance_list)


# -----------------------------
# MAIN ENTRY
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
