from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
import sqlite3
import os
from datetime import datetime
import json
from werkzeug.utils import secure_filename

from init_admin_db import init_db
from admin import admin_bp

app = Flask(__name__)
app.secret_key = 'prarambha_admin_secret_2026'
app.register_blueprint(admin_bp)

# Automatically initialize database for Vercel environments (Serverless)
init_db()

if os.environ.get('VERCEL') == '1':
    DATABASE = '/tmp/admissions.db'
else:
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admissions.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- USER SIDE ROUTES ---

@app.route('/')
def index():
    # Helper for the student form
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(CAST(application_no AS INTEGER)) FROM applications')
    result = cursor.fetchone()[0]
    app_no = '0' if result is None else str(result + 1)
    conn.close()
    return render_template('index.html', app_no=app_no)

DOC_MAP = {
    'document_sslc_upload': 'Original SSLC Marks Card',
    'document_puc_upload': 'Original PUC Marks Card',
    'document_tc_upload': 'Transfer Certificate (TC)',
    'document_conduct_upload': 'Conduct Certificate',
    'document_caste_upload': 'Caste Certificate',
    'document_income_upload': 'Income Certificate',
    'document_aadhar_upload': 'Aadhar Card Copy',
    'document_photos_upload': 'Photos (5 Passport size)'
}

@app.route('/submit', methods=['POST'])
def submit_application():
    try:
        data = request.form
        programs = request.form.getlist('program')
        languages = request.form.getlist('language')
        
        # PIN code collection
        pin = "".join([data.get(f'pin_{i}', '') for i in range(1, 7)])
        
        # Save documents
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        uploaded_docs = {}
        app_no = data.get('app_no', 'unknown')
        
        for field_name, doc_type in DOC_MAP.items():
            if field_name in request.files:
                file = request.files[field_name]
                if file and file.filename != '':
                    filename = f"{app_no}_{field_name}_{secure_filename(file.filename)}"
                    file.save(os.path.join(uploads_dir, filename))
                    uploaded_docs[doc_type] = f"/static/uploads/{filename}"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO applications (
                application_no, name, whatsapp, gender,
                dob_date, dob_month, dob_year,
                nationality, email, aadhar, blood_group, pan,
                village, taluk, district, religion, caste, category,
                parent_name, occupation, postal_address, parent_phone,
                annual_income, permanent_address, pin_code,
                program, second_language, status,
                college_attended, first_puc, second_puc,
                qual_exam_name, qual_exam_reg_no, qual_exam_year, qual_exam_board,
                qual_exam_marks_obtained, qual_exam_max_marks, qual_exam_percentage,
                submitted_documents
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            app_no, data.get('name'), data.get('whatsapp'), data.get('gender'),
            data.get('dob-date'), data.get('dob-month'), data.get('dob-year'),
            data.get('nationality'), data.get('email'), data.get('aadhar'), data.get('blood-group'), data.get('pan'),
            data.get('village'), data.get('taluk'), data.get('district'), data.get('religion'), data.get('caste'), data.get('category'),
            data.get('parent-name'), data.get('occupation'), data.get('postal-address'), data.get('parent-phone'),
            data.get('annual-income'), data.get('permanent-address'), pin,
            ', '.join(programs), ', '.join(languages),
            data.get('college-attended'), data.get('first-puc'), data.get('second-puc'),
            data.get('qual-exam-name'), data.get('qual-exam-reg-no'), data.get('qual-exam-year'), data.get('qual-exam-board'),
            data.get('qual-exam-marks'), data.get('qual-exam-max'), data.get('qual-exam-percent'),
            json.dumps(uploaded_docs)
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Submitted!', 'application_no': app_no})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/applications')
def applications():
    conn = get_db()
    raw_apps = conn.execute('SELECT * FROM applications ORDER BY created_at DESC').fetchall()
    applications = [dict(row) for row in raw_apps]
    conn.close()
    return render_template('applications.html', applications=applications)

@app.route('/application/<int:application_id>')
def application_detail(application_id):
    conn = get_db()
    application_raw = conn.execute('SELECT * FROM applications WHERE id = ?', (application_id,)).fetchone()
    conn.close()
    if application_raw is None:
        abort(404)
    application = dict(application_raw)
    
    # Parse submitted_documents
    docs = {}
    if application.get('submitted_documents'):
        try:
            docs = json.loads(application['submitted_documents'])
        except Exception:
            pass
    application['parsed_documents'] = docs
    
    return render_template('application_detail.html', app=application)

if __name__ == '__main__':
    # Ensure tables exist and initial admin account is seeded.
    init_db()
    
    # Copy the cropped logo image to static directory
    import shutil
    src_logo = r"C:\Users\HP\.gemini\antigravity-ide\brain\0c413ffb-af48-4672-94b2-46435dd014b3\college_logo_cropped_1779875132400.png"
    dst_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'college-logo.png')
    if os.path.exists(src_logo):
        try:
            shutil.copy(src_logo, dst_logo)
        except Exception as e:
            print("Logo copy error:", e)
            
    app.run(debug=True, port=5000)
