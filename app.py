import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g

app = Flask(__name__)
app.secret_key = "your_secret_key_here"
DATABASE = "academy.db"

def get_db():
    """Return a database connection for the current application context."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection at the end of each request."""
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    """Create all tables if they don't exist."""
    with app.app_context():
        db = get_db()
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
            -- 'student', 'teacher', 'admin'
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


# -----------------------------
# GENERAL ROUTES
# -----------------------------
@app.route("/")
def index():
    """
    Homepage with quick links to admin, teacher, and student login,
    plus a link to register.
    """
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Single registration page.
    In a real scenario, you may want separate ways to add admins vs. students.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]  # student, teacher, admin

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, role)
            )
            db.commit()
        except sqlite3.IntegrityError:
            return "Error: That username is already taken. Please choose another."

        # After successful registration, direct them to their role-specific login
        if role == "admin":
            return redirect(url_for("admin_login"))
        elif role == "teacher":
            return redirect(url_for("teacher_login"))
        else:
            return redirect(url_for("student_login"))

    return render_template("register.html")

@app.route("/logout")
def logout():
    """Log out any user (admin/teacher/student)."""
    session.clear()
    return redirect(url_for("index"))


# -----------------------------
# SEPARATE LOGIN ROUTES
# -----------------------------

# ADMIN LOGIN
@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ? AND role = 'admin'",
            (username, password)
        )
        admin_user = cursor.fetchone()

        if admin_user:
            session["user_id"] = admin_user["id"]
            session["role"] = admin_user["role"]
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin Credentials!"

    return render_template("admin_login.html")


# TEACHER LOGIN
@app.route("/login/teacher", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ? AND role = 'teacher'",
            (username, password)
        )
        teacher_user = cursor.fetchone()

        if teacher_user:
            session["user_id"] = teacher_user["id"]
            session["role"] = teacher_user["role"]
            return redirect(url_for("teacher_dashboard"))
        else:
            return "Invalid Teacher Credentials!"

    return render_template("teacher_login.html")


# STUDENT LOGIN
@app.route("/login/student", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ? AND role = 'student'",
            (username, password)
        )
        student_user = cursor.fetchone()

        if student_user:
            session["user_id"] = student_user["id"]
            session["role"] = student_user["role"]
            return redirect(url_for("student_dashboard"))
        else:
            return "Invalid Student Credentials!"

    return render_template("student_login.html")


# -----------------------------
# ADMIN-ONLY ROUTES
# -----------------------------
@app.route("/admin/dashboard")
def admin_dashboard():
    """
    Dashboard for admin users only.
    """
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admins Only."
    return render_template("admin_dashboard.html")

@app.route("/admin/manage_courses", methods=["GET", "POST"])
def manage_courses():
    """
    Admin can create, edit, delete courses here.
    """
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admins Only."

    db = get_db()

    # Add new course (if POST request)
    if request.method == "POST":
        course_name = request.form["course_name"]
        semester = request.form["semester"]
        db.execute("INSERT INTO courses (name, semester) VALUES (?, ?)",
                   (course_name, semester))
        db.commit()
        return redirect(url_for("manage_courses"))

    # Show existing courses
    cursor = db.execute("SELECT * FROM courses")
    courses = cursor.fetchall()
    return render_template("manage_courses.html", courses=courses)

@app.route("/admin/delete_course/<int:course_id>", methods=["POST"])
def delete_course(course_id):
    """
    Delete a course (admin only).
    """
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admins Only."

    db = get_db()
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()
    return redirect(url_for("manage_courses"))

@app.route("/admin/edit_course/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):
    """
    Edit a course (admin only).
    """
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admins Only."

    db = get_db()
    if request.method == "POST":
        course_name = request.form["course_name"]
        semester = request.form["semester"]
        db.execute("UPDATE courses SET name = ?, semester = ? WHERE id = ?",
                   (course_name, semester, course_id))
        db.commit()
        return redirect(url_for("manage_courses"))
    else:
        cursor = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        course = cursor.fetchone()
        # Reuse 'enroll.html' for editing or create a separate template
        return render_template("enroll.html", course=course, is_edit=True)


# -----------------------------
# TEACHER-ONLY ROUTES
# -----------------------------
@app.route("/teacher/dashboard")
def teacher_dashboard():
    """
    Dashboard for teacher users only.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teachers Only."
    return render_template("teacher_dashboard.html")

@app.route("/teacher/courses")
def teacher_courses():
    """
    List of courses (teacher may see all or just the ones they handle).
    For simplicity, let's show all, and the teacher can pick one to mark attendance.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teachers Only."

    db = get_db()
    cursor = db.execute("SELECT * FROM courses")
    course_list = cursor.fetchall()
    return render_template("courses.html", courses=course_list, is_teacher=True)

@app.route("/teacher/course_attendance/<int:course_id>", methods=["GET"])
def course_attendance(course_id):
    """
    Page for teachers to mark attendance for all students enrolled in a specific course.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teachers Only."

    db = get_db()
    # Get course details
    course_cursor = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    course = course_cursor.fetchone()

    # Get all enrollments for this course (with student info)
    enrollment_cursor = db.execute("""
        SELECT e.id AS enrollment_id, u.username AS student_name
        FROM enrollments e
        JOIN users u ON e.user_id = u.id
        WHERE e.course_id = ?
    """, (course_id,))
    enrollments = enrollment_cursor.fetchall()

    return render_template("course_attendance.html", course=course, enrollments=enrollments)

@app.route("/teacher/process_attendance/<int:course_id>", methods=["POST"])
def process_attendance(course_id):
    """
    Teacher's POST request to record attendance for multiple students at once.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teachers Only."

    date = request.form.get("attendance_date")
    db = get_db()

    # For each status_<enrollment_id> in the form
    for key in request.form:
        if key.startswith("status_"):
            enrollment_id_str = key.split("_")[1]  # e.g. "status_3" -> "3"
            enrollment_id = int(enrollment_id_str)
            status = request.form[key]  # "present" or "absent"

            db.execute(
                "INSERT INTO attendance (enrollment_id, date, status) VALUES (?, ?, ?)",
                (enrollment_id, date, status)
            )
    db.commit()

    return redirect(url_for("teacher_dashboard"))


# -----------------------------
# STUDENT-ONLY ROUTES
# -----------------------------
@app.route("/student/dashboard")
def student_dashboard():
    """
    Dashboard for student users only.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Students Only."
    return render_template("student_dashboard.html")

@app.route("/courses")
def courses():
    """
    List all available courses for student enrollment.
    (Public route or restricted to student? We'll allow any logged-in user, but logically for students.)
    """
    if "user_id" not in session:
        return redirect(url_for("index"))

    # If strictly for students, un-comment next lines:
    # if session.get("role") != "student":
    #     return "Access Denied. Students Only."

    db = get_db()
    cursor = db.execute("SELECT * FROM courses")
    course_list = cursor.fetchall()
    return render_template("courses.html", courses=course_list, is_teacher=(session.get("role") == "teacher"))

@app.route("/enroll/<int:course_id>", methods=["GET", "POST"])
def enroll(course_id):
    """
    Student enrolls in a course.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Students Only."

    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)",
            (session["user_id"], course_id)
        )
        db.commit()
        return redirect(url_for("my_enrollments"))

    db = get_db()
    cursor = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()
    return render_template("enroll.html", course=course, is_edit=False)

@app.route("/my_enrollments")
def my_enrollments():
    """
    Shows all courses the student is enrolled in.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Students Only."

    db = get_db()
    cursor = db.execute("""
        SELECT e.id AS enrollment_id, c.name AS course_name, c.semester AS semester
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.user_id = ?
    """, (session["user_id"],))
    enrollments = cursor.fetchall()
    return render_template("my_enrollments.html", enrollments=enrollments)


# -----------------------------
# MAIN ENTRY
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
