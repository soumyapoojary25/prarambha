import sqlite3
import os

DATABASE = 'admissions.db'

def migrate():
    if not os.path.exists(DATABASE):
        print("Database not found. No migration needed (will be created by app).")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get current columns
    cursor.execute('PRAGMA table_info(applications)')
    columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = [
        ('qual_exam_name', 'TEXT'),
        ('qual_exam_reg_no', 'TEXT'),
        ('qual_exam_year', 'TEXT'),
        ('qual_exam_board', 'TEXT'),
        ('qual_exam_marks_obtained', 'TEXT'),
        ('qual_exam_max_marks', 'TEXT'),
        ('qual_exam_percentage', 'TEXT'),
        ('submitted_documents', 'TEXT')
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding column {col_name}...")
            cursor.execute(f'ALTER TABLE applications ADD COLUMN {col_name} {col_type}')
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == '__main__':
    migrate()
