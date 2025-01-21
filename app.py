import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g
import os
from flask import send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Replace with a secure, random key
DATABASE = "academy.db"

# Add or update this in app.py:
UPLOAD_FOLDER = 'uploads'  # or any directory name you prefer
ALLOWED_EXTENSIONS = {'pdf'}  # only PDF files

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/student/download/<int:resource_id>")
def download_pdf(resource_id):
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."

    db = get_db()
    resource = db.execute("""
        SELECT file_path 
        FROM course_resources 
        WHERE id = ?
    """, (resource_id,)).fetchone()

    if not resource:
        return "Resource not found."

    # Serve the file for download
    return send_file(resource["file_path"], as_attachment=True)

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

@app.route("/update_profile", methods=["GET", "POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    db = get_db()

    # Fetch current user details (including password)
    user = db.execute("""
        SELECT username, actual_name, password
          FROM users
         WHERE id = ?
    """, (user_id,)).fetchone()

    if request.method == "POST":
        new_username = request.form["username"]
        new_actual_name = request.form["actual_name"]
        current_password_input = request.form["current_password"]
        new_password = request.form["new_password"]

        # Verify current (old) password
        if current_password_input != user["password"]:
            return "Error: The current password you entered is incorrect."

        # If the old password matches, apply updates
        db.execute("""
            UPDATE users
               SET username = ?,
                   actual_name = ?,
                   password = ?
             WHERE id = ?
        """, (new_username, new_actual_name, new_password, user_id))
        db.commit()

        # (Optional) update session if username changed
        session["username"] = new_username

        return redirect(url_for(f"{session['role']}_dashboard"))

    return render_template("update_profile.html", user=user)


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

@app.route("/admin/assign_course", methods=["GET", "POST"])
def assign_course():
    if "user_id" not in session or session.get("role") != "admin":
        return "Access Denied. Admin Only."

    db = get_db()
    if request.method == "POST":
        course_id = request.form["course_id"]
        teacher_id = request.form["teacher_id"]
        # Update the teacher assignment for the course
        db.execute("UPDATE courses SET teacher_id = ? WHERE id = ?", (teacher_id, course_id))
        db.commit()
        return redirect(url_for("assign_course"))

    # GET request: show form to assign courses
    courses = db.execute("SELECT * FROM courses").fetchall()
    teachers = db.execute("SELECT * FROM users WHERE role = 'teacher'").fetchall()
    return render_template("assign_course.html", courses=courses, teachers=teachers)


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
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    # Fetch courses the teacher is associated with; for now, all courses
    your_courses = db.execute("SELECT * FROM courses").fetchall()

    return render_template("teacher_dashboard.html", your_courses=your_courses)

@app.route("/teacher/course_grades/<int:course_id>", methods=["GET"])
def course_grades(course_id):
    """
    Displays all enrolled students in a course and their grades.
    Teacher can add or update a grade for each category.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    # Check if the teacher is assigned to this course (optional if you track teacher_id)
    # For now, skip or do a check if courses.teacher_id == session["user_id"]

    # Fetch course info
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        return "Course not found."

    # Get all enrollments for this course with student user info
    enrollments = db.execute("""
        SELECT e.id AS enrollment_id, u.username, u.actual_name
          FROM enrollments e
          JOIN users u ON e.user_id = u.id
         WHERE e.course_id = ?
    """, (course_id,)).fetchall()

    # We'll also want to fetch existing grades for each enrollment
    # so teacher can see or update them
    # Instead of a complicated join, you can fetch them inside the template or do a dictionary approach
    grades = db.execute("""
        SELECT g.id, g.enrollment_id, g.grade_value, g.category
          FROM grades g
          JOIN enrollments e ON g.enrollment_id = e.id
         WHERE e.course_id = ?
    """, (course_id,)).fetchall()

    # For convenience, convert grades into a dict keyed by (enrollment_id, category)
    grade_dict = {}
    for g in grades:
        grade_dict[(g["enrollment_id"], g["category"])] = g["grade_value"]

    return render_template("teacher_course_grades.html",
                           course=course,
                           enrollments=enrollments,
                           grade_dict=grade_dict)

@app.route("/teacher/submit_grades/<int:course_id>", methods=["POST"])
def submit_grades(course_id):
    """
    Processes the teacher's submission for multiple (enrollment_id, category, grade) entries.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    # Suppose we get multiple fields in the form: "grade_{enrollment_id}_{category}"
    # Example key: "grade_5_Assignment" => value "85"
    for key, value in request.form.items():
        if key.startswith("grade_"):
            # parse out enrollment_id and category
            # e.g. key: "grade_5_Assignment"
            parts = key.split("_", 2)  # ["grade", "5", "Assignment"]
            if len(parts) < 3:
                continue
            enrollment_id = parts[1]
            category = parts[2]      # e.g. "Assignment", "Quiz", "Midterm"
            grade_value = value

            # Check if row exists
            existing = db.execute("""
                SELECT id
                  FROM grades
                 WHERE enrollment_id = ?
                   AND category = ?
            """, (enrollment_id, category)).fetchone()

            if existing:
                # update
                db.execute("""
                    UPDATE grades
                       SET grade_value = ?
                     WHERE id = ?
                """, (grade_value, existing["id"]))
            else:
                # insert
                db.execute("""
                    INSERT INTO grades (enrollment_id, grade_value, category)
                    VALUES (?, ?, ?)
                """, (enrollment_id, grade_value, category))
    db.commit()

    return redirect(url_for("course_grades", course_id=course_id))

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
# TEACHER: PDF Resource Management
# -----------------------------

@app.route("/teacher/course_resources/<int:course_id>")
def teacher_course_resources(course_id):
    """
    Lists all PDFs uploaded for the specified course.
    Teacher can see, upload, delete, or update (rename).
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    # Get the course info
    course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        return "Course not found."

    # Get all resources for this course
    resources = db.execute("""
        SELECT id, file_name, file_path
          FROM course_resources
         WHERE course_id = ?
    """, (course_id,)).fetchall()

    # Render a template like teacher_course_resources.html
    return render_template("teacher_course_resources.html",
                           course=course, resources=resources)


@app.route("/teacher/upload_resource/<int:course_id>", methods=["POST"])
def upload_resource(course_id):
    """
    Handles the PDF upload for a specific course.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    # Check if the course exists
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        return "Course not found."

    if 'pdf_file' not in request.files:
        return "No file part in request."

    file = request.files['pdf_file']
    if file.filename == '':
        return "No file selected."

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Create a subfolder for each course if desired
        course_folder = os.path.join(app.config['UPLOAD_FOLDER'], f"course_{course_id}")
        os.makedirs(course_folder, exist_ok=True)
        
        # Full path where the file will be saved
        file_path = os.path.join(course_folder, filename)
        file.save(file_path)

        # Insert metadata into DB
        db.execute("""
            INSERT INTO course_resources (course_id, file_name, file_path)
            VALUES (?, ?, ?)
        """, (course_id, filename, file_path))
        db.commit()

        return redirect(url_for("teacher_course_resources", course_id=course_id))
    else:
        return "File type not allowed. Only PDF files are permitted."


@app.route("/teacher/delete_resource/<int:resource_id>", methods=["POST"])
def delete_resource(resource_id):
    """
    Deletes a PDF resource from DB and the filesystem.
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    resource = db.execute("""
        SELECT course_id, file_path
          FROM course_resources
         WHERE id = ?
    """, (resource_id,)).fetchone()

    if not resource:
        return "Resource not found."

    # Delete from DB
    db.execute("DELETE FROM course_resources WHERE id=?", (resource_id,))
    db.commit()

    # Also delete the actual file if it exists
    if os.path.exists(resource['file_path']):
        os.remove(resource['file_path'])

    return redirect(url_for("teacher_course_resources", course_id=resource['course_id']))


@app.route("/teacher/update_resource/<int:resource_id>", methods=["GET", "POST"])
def update_resource(resource_id):
    """
    Allows teacher to rename the resource file_name in DB. 
    (This does not rename the physical file, but you could if desired.)
    """
    if "user_id" not in session or session.get("role") != "teacher":
        return "Access Denied. Teacher Only."

    db = get_db()
    resource = db.execute("""
        SELECT id, course_id, file_name, file_path
          FROM course_resources
         WHERE id = ?
    """, (resource_id,)).fetchone()

    if not resource:
        return "Resource not found."

    if request.method == "POST":
        new_name = request.form["file_name"]
        db.execute("UPDATE course_resources SET file_name = ? WHERE id = ?",
                   (new_name, resource_id))
        db.commit()

        # Optional: If you want to rename the actual file on disk, you'd do so here.
        # e.g. old_path = resource['file_path']
        # new_basename = secure_filename(new_name)
        # new_path = os.path.join(os.path.dirname(old_path), new_basename)
        # os.rename(old_path, new_path)
        # update DB's file_path as well

        return redirect(url_for("teacher_course_resources", course_id=resource["course_id"]))
    else:
        # Render a small form for teacher to rename 'file_name'
        return render_template("teacher_update_resource.html", resource=resource)

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
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."

    db = get_db()
    enrollments = db.execute("""
        SELECT e.course_id, c.name AS course_name, c.semester
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.user_id = ?
    """, (session["user_id"],)).fetchall()

    return render_template("student_dashboard.html", enrollments=enrollments)


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
# STUDENT: View/Download PDF Resources
# -----------------------------
@app.route("/student/resources/<int:course_id>")
def student_resources(course_id):
    """
    Lists PDFs for a course if the student is enrolled.
    Student can download/view them.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."

    db = get_db()
    # Check if student is enrolled in this course
    enrollment_check = db.execute("""
        SELECT e.id
          FROM enrollments e
         WHERE e.course_id = ?
           AND e.user_id = ?
    """, (course_id, session["user_id"])).fetchone()

    if not enrollment_check:
        return "You are not enrolled in this course."

    # Fetch all resources
    resources = db.execute("""
        SELECT id, file_name, file_path
          FROM course_resources
         WHERE course_id = ?
    """, (course_id,)).fetchall()

    # Render a template like "student_course_resources.html" listing them
    return render_template("student_course_resources.html", resources=resources)

@app.route("/student/my_grades")
def my_grades():
    """
    Shows the logged-in student all of their grades by course and category.
    """
    if "user_id" not in session or session.get("role") != "student":
        return "Access Denied. Student Only."

    db = get_db()
    # fetch courses & grades for this student
    # step 1: find all enrollments
    enrollments = db.execute("""
        SELECT e.id AS enrollment_id, c.name AS course_name, c.semester
          FROM enrollments e
          JOIN courses c ON e.course_id = c.id
         WHERE e.user_id = ?
    """, (session["user_id"],)).fetchall()

    # step 2: fetch all grades for these enrollments
    enrollment_ids = [str(e["enrollment_id"]) for e in enrollments]
    if not enrollment_ids:
        return "No enrollments found."

    # Convert to comma-separated string if needed, or do a parameterized query
    in_clause = ",".join(enrollment_ids)  # e.g. "3,4,5"
    grades = db.execute(f"""
        SELECT g.enrollment_id, g.category, g.grade_value
          FROM grades g
         WHERE g.enrollment_id IN ({in_clause})
    """).fetchall()

    # Build a structure to map enrollment_id -> {category: grade_value}
    from collections import defaultdict
    grades_map = defaultdict(dict)
    for g in grades:
        grades_map[g["enrollment_id"]][g["category"]] = g["grade_value"]

    return render_template("student_my_grades.html",
                           enrollments=enrollments,
                           grades_map=grades_map)

# -----------------------------
# MAIN ENTRY
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run()
