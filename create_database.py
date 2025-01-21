import sqlite3

def create_db():
    conn = sqlite3.connect("academy.db")
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            actual_name TEXT
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            semester TEXT NOT NULL,
            teacher_id INTEGER,
            FOREIGN KEY(teacher_id) REFERENCES users(id)
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
             category TEXT,              -- e.g. "Assignment", "Quiz", "Midterm", etc.
             FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
);


        CREATE TABLE IF NOT EXISTS course_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            FOREIGN KEY(course_id) REFERENCES courses(id)
        );
    """)

    # Create default admin if none found
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    admin_exist = cursor.fetchone()
    if not admin_exist:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       ("admin", "admin123", "admin"))
        conn.commit()

    conn.commit()
    conn.close()
    print("Database schema created, default admin: admin/admin123")

if __name__ == "__main__":
    create_db()
