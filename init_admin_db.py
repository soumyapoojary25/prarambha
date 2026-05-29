import sqlite3
import os

if os.environ.get('VERCEL') == '1':
    DATABASE = '/tmp/admissions.db'
else:
    DATABASE = 'admissions.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 1. Admin Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # 1.5 Applications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_no TEXT UNIQUE,
            name TEXT,
            whatsapp TEXT,
            gender TEXT,
            dob_date TEXT,
            dob_month TEXT,
            dob_year TEXT,
            nationality TEXT,
            email TEXT,
            aadhar TEXT,
            blood_group TEXT,
            pan TEXT,
            village TEXT,
            taluk TEXT,
            district TEXT,
            religion TEXT,
            caste TEXT,
            category TEXT,
            parent_name TEXT,
            occupation TEXT,
            postal_address TEXT,
            parent_phone TEXT,
            annual_income TEXT,
            permanent_address TEXT,
            pin_code TEXT,
            program TEXT,
            second_language TEXT,
            status TEXT DEFAULT 'pending',
            course TEXT,
            approved_at TEXT,
            college_attended TEXT,
            first_puc TEXT,
            second_puc TEXT,
            qual_exam_name TEXT,
            qual_exam_reg_no TEXT,
            qual_exam_year TEXT,
            qual_exam_board TEXT,
            qual_exam_marks_obtained TEXT,
            qual_exam_max_marks TEXT,
            qual_exam_percentage TEXT,
            submitted_documents TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Courses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            total_seats INTEGER NOT NULL,
            available_seats INTEGER NOT NULL
        )
    ''')

    # 3. Seats Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            seat_label TEXT,
            status TEXT DEFAULT 'available', -- available, occupied, selected
            student_id INTEGER NULL,
            FOREIGN KEY(course_id) REFERENCES courses(id),
            FOREIGN KEY(student_id) REFERENCES applications(id)
        )
    ''')
    
    # Check if applications table has columns, if not add them
    additional_cols = [
        ('status', "TEXT DEFAULT 'pending'"),
        ('course', "TEXT"),
        ('approved_at', "TEXT"),
        ('college_attended', "TEXT"),
        ('first_puc', "TEXT"),
        ('second_puc', "TEXT"),
        ('qual_exam_name', "TEXT"),
        ('qual_exam_reg_no', "TEXT"),
        ('qual_exam_year', "TEXT"),
        ('qual_exam_board', "TEXT"),
        ('qual_exam_marks_obtained', "TEXT"),
        ('qual_exam_max_marks', "TEXT"),
        ('qual_exam_percentage', "TEXT"),
        ('submitted_documents', "TEXT")
    ]
    for col_name, col_def in additional_cols:
        try:
            cursor.execute(f"ALTER TABLE applications ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass

    # 4. Course Seats Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS course_seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT UNIQUE NOT NULL,
            total_seats INTEGER NOT NULL,
            filled_seats INTEGER NOT NULL DEFAULT 0,
            remaining_seats INTEGER NOT NULL
        )
    ''')

    # 5. Notifications Table (Optional but requested)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed initial Admin (Password: admin123)
    cursor.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin123'))

    # Seed initial course_seats
    initial_seats = [
        ('BCA', 180, 180),
        ('BCom', 80, 80),
        ('BBA', 110, 110)
    ]
    for course_name, total, remaining in initial_seats:
        cursor.execute('''
            INSERT OR IGNORE INTO course_seats (course_name, total_seats, filled_seats, remaining_seats)
            VALUES (?, ?, 0, ?)
        ''', (course_name, total, remaining))

    # Seed initial Courses (old system fallback compatibility)
    courses = [
        ('B.Com', 60, 60),
        ('BCA', 180, 180),
        ('BBA', 110, 110),
        ('B.Sc', 20, 20)
    ]
    for course in courses:
        cursor.execute("INSERT OR IGNORE INTO courses (name, total_seats, available_seats) VALUES (?, ?, ?)", course)
        
        # Get the course id
        cursor.execute("SELECT id FROM courses WHERE name = ?", (course[0],))
        course_id = cursor.fetchone()[0]
        
        # Create physical seats for the grid (old system compatibility)
        for i in range(1, course[1] + 1):
            cursor.execute("INSERT OR IGNORE INTO seats (course_id, seat_label) VALUES (?, ?)", (course_id, f"S{i}"))

    # Force update existing records in course_seats to the new seats limits
    cursor.execute("UPDATE course_seats SET total_seats = 180, remaining_seats = 180 - filled_seats WHERE course_name = 'BCA'")
    cursor.execute("UPDATE course_seats SET total_seats = 110, remaining_seats = 110 - filled_seats WHERE course_name = 'BBA'")
    
    # Force update existing records in courses to new seat capacities
    cursor.execute("UPDATE courses SET total_seats = 180, available_seats = 180 - (total_seats - available_seats) WHERE name = 'BCA'")
    cursor.execute("UPDATE courses SET total_seats = 110, available_seats = 110 - (total_seats - available_seats) WHERE name = 'BBA'")

    conn.commit()
    conn.close()
    print("Database finalized for Prarambha Admin Dashboard (BCA=180, BBA=110).")

if __name__ == '__main__':
    init_db()
