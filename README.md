# KD Academy - Web Application

KD Academy is a web-based application built using Flask to facilitate student course enrollment, attendance tracking, grading, and resource management. The system aims to improve administrative efficiency and enhance the student learning experience by digitizing various front-office services.

---

## 🚀 Features

### Admin Functionalities
- Create and manage teacher and student accounts.
- Assign courses to teachers.
- Monitor course enrollments.
- Manage subject offerings for each semester.

### Teacher Functionalities
- Manage student attendance records.
- Upload and manage course-related PDFs (assignments, lecture slides, etc.).
- Grade students for assignments, quizzes, projects, midterm, and final exams.
- View and update student records.

### Student Functionalities
- Enroll in available courses.
- View/download course-related PDFs.
- Track attendance records for enrolled courses.
- View assignment and exam grades.

---

## 🏗️ Technology Stack

- **Frontend:** HTML5, CSS3, JavaScript
- **Backend:** Flask (Python)
- **Database:** SQLite3
- **Other Tools:** Bootstrap (for styling), Jinja2 (templating), Flask-WTF (forms), Flask-Login (authentication)

---

## ⚙️ Installation

Follow these steps to set up the project locally:

### 1. Clone the Repository

```bash
https://github.com/shahabaalam/School_Management_System.git
cd file_name
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:

- On Windows:
  ```bash
  venv\Scripts\activate
  ```

- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize the Database

Run the following command to create the necessary tables:

```bash
python create_database.py
```

*(Ensure `create_database.py` contains the logic for initializing the database schema.)*

### 5. Run the Application

```bash
python app.py
or
flask run
```

The application will be available at:  
**http://127.0.0.1:5000**
---

## 🛠️ Usage

1. **Admin Login**  
   - Use default credentials (e.g., `admin/admin123`) to access the admin dashboard.
   - Assign courses to teachers and manage student accounts.

2. **Teacher Login**  
   - Manage student attendance and upload course materials.
   - Grade students based on assignments, quizzes, and exams.

3. **Student Login**  
   - Enroll in available courses.
   - View attendance records and grades.

---

## 📂 Project Structure

```
kd-academy/
│-- static/                 # Static files (CSS, JS)
│   │-- script.js            # JavaScript for frontend interactions
│   │-- style.css            # Styling for the application
│
│-- templates/              # HTML templates for Flask views
│-- uploads/                # Directory for storing uploaded files (e.g., PDFs)
│-- web_dev/                 # Additional project-related files or modules
│
│-- .gitignore               # Git ignore file for excluding files like database, venv, etc.
│-- academy.db                # SQLite database file
│-- app.py                    # Main Flask application
│-- create_database.py        # Database initialization script
│-- requirements.txt          # Python dependencies
```

---

## 🔒 Environment Variables

Create a `.env` file in the project root and define the following environment variables:

```
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///instance/database.db
```

---

## ✅ To-Do List

- [ ] Implement user roles with permissions more efficiently.
- [ ] Add automated email notifications for enrollment confirmations.
- [ ] Improve the UI with better CSS/JS frameworks (e.g., Tailwind or React).

---

## 🤝 Contributing

Contributions are welcome! Follow these steps to contribute:

1. Fork the repository.
2. Create a new branch (`feature-branch`).
3. Commit your changes.
4. Push to the forked repository.
5. Open a pull request.

---

## 🐛 Reporting Issues

If you find any bugs or issues, please open an issue in the GitHub repository with a detailed description.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

## 📧 Contact

If you have any questions or suggestions, feel free to reach out:

- Email: shahaba.alam@student.aiu.edu.my
