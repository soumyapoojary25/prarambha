from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
import sqlite3
import os
from datetime import datetime
import json
from werkzeug.utils import secure_filename
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from init_admin_db import init_db
from admin import admin_bp


def is_vercel():
    return bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))


# Get the root directory for proper static/template paths in serverless
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ROOT_DIR, 'static')
TEMPLATES_DIR = os.path.join(ROOT_DIR, 'templates')

app = Flask(__name__, 
            static_folder=STATIC_DIR,
            static_url_path='/static',
            template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'prarambha_admin_secret_2026')

# Register admin blueprint with error handling
try:
    app.register_blueprint(admin_bp)
    logger.info("Admin blueprint registered successfully")
except Exception as e:
    logger.error(f"Failed to register admin blueprint: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    raise

# Error handlers for debugging
@app.before_request
def log_request():
    logger.info(f"Request: {request.method} {request.path}")

@app.errorhandler(404)
def handle_404(e):
    logger.error(f"404 Error: {request.path} - {str(e)}")
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def handle_500(e):
    logger.error(f"500 Error on {request.method} {request.path}: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    return jsonify({'error': str(e)}), 500


class _VercelPathMiddleware:
    """Strip serverless path prefixes so Flask routes match on Vercel."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        original_path = path
        
        # On Vercel, the PATH_INFO may or may not have /api prefix depending on routing
        # We need to handle both cases: /api/admin/... and /admin/...
        if path.startswith('/api/index/'):
            environ['PATH_INFO'] = path[len('/api/index'):] or '/'
        elif path == '/api/index':
            environ['PATH_INFO'] = '/'
        # If path doesn't start with /api, leave it as is (Vercel may route directly)
        
        return self.wsgi_app(environ, start_response)


if is_vercel():
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    except ImportError:
        pass
    app.wsgi_app = _VercelPathMiddleware(app.wsgi_app)

# Initialize database (ephemeral /tmp on Vercel)
try:
    init_db()
except Exception as e:
    print(f'init_db warning: {e}')

if is_vercel():
    DATABASE = '/tmp/admissions.db'
else:
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admissions.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- USER SIDE ROUTES ---

@app.route('/health')
def health():
    """Deployment health check (use /health on Vercel to verify the app is running)."""
    return jsonify({'status': 'ok', 'service': 'prarambha-admissions'}), 200


@app.route('/')
def index():
    app_id = request.args.get('id')
    application = None
    app_no = None
    
    conn = get_db()
    cursor = conn.cursor()
    
    if app_id:
        try:
            cursor.execute('SELECT * FROM applications WHERE id = ?', (int(app_id),))
            row = cursor.fetchone()
            if row:
                application = dict(row)
                app_no = application['application_no']
                # Parse submitted_documents
                docs = {}
                if application.get('submitted_documents'):
                    try:
                        docs = json.loads(application['submitted_documents'])
                    except Exception:
                        pass
                application['parsed_documents'] = docs
        except Exception as e:
            print("Error loading application for editing:", e)
            
    if not app_no:
        cursor.execute('SELECT MAX(CAST(application_no AS INTEGER)) FROM applications')
        result = cursor.fetchone()[0]
        app_no = '1' if (result is None or result < 1) else str(result + 1)
        
    conn.close()
    return render_template('index.html', app_no=app_no, application=application)

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

def get_dob_fields(data):
    """Read DOB from day/month/year selects (supports legacy field names)."""
    day = (data.get('dob-date') or data.get('dob-day') or '').strip()
    month = (data.get('dob-month') or '').strip()
    year = (data.get('dob-year') or '').strip()
    return day, month, year


@app.route('/submit', methods=['POST'])
def submit_application():
    try:
        data = request.form
        programs = request.form.getlist('program')
        languages = request.form.getlist('language')
        dob_date, dob_month, dob_year = get_dob_fields(data)
        
        # PIN code collection
        pin = "".join([data.get(f'pin_{i}', '') for i in range(1, 7)])
        
        # Save documents
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        app_no = data.get('app_no', 'unknown')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if application already exists
        cursor.execute('SELECT id, submitted_documents FROM applications WHERE application_no = ?', (app_no,))
        existing = cursor.fetchone()
        
        uploaded_docs = {}
        if existing:
            # Load existing docs
            if existing['submitted_documents']:
                try:
                    uploaded_docs = json.loads(existing['submitted_documents'])
                except Exception:
                    pass
            
            # Save new files and delete overridden ones
            for field_name, doc_type in DOC_MAP.items():
                if field_name in request.files:
                    file = request.files[field_name]
                    if file and file.filename != '':
                        # Delete old file
                        if doc_type in uploaded_docs:
                            old_file_path = os.path.join(app.root_path, uploaded_docs[doc_type].lstrip('/'))
                            if os.path.exists(old_file_path):
                                try:
                                    os.remove(old_file_path)
                                except Exception as e:
                                    print("Error deleting old file:", e)
                        
                        # Save new file
                        filename = f"{app_no}_{field_name}_{secure_filename(file.filename)}"
                        file.save(os.path.join(uploads_dir, filename))
                        uploaded_docs[doc_type] = f"/static/uploads/{filename}"
            
            cursor.execute('''
                UPDATE applications SET
                    name = ?, whatsapp = ?, gender = ?,
                    dob_date = ?, dob_month = ?, dob_year = ?,
                    nationality = ?, email = ?, aadhar = ?, blood_group = ?, pan = ?,
                    village = ?, taluk = ?, district = ?, religion = ?, caste = ?, category = ?,
                    parent_name = ?, occupation = ?, postal_address = ?, parent_phone = ?,
                    annual_income = ?, permanent_address = ?, pin_code = ?,
                    program = ?, second_language = ?,
                    college_attended = ?, first_puc = ?, second_puc = ?,
                    qual_exam_name = ?, qual_exam_reg_no = ?, qual_exam_year = ?, qual_exam_board = ?,
                    qual_exam_marks_obtained = ?, qual_exam_max_marks = ?, qual_exam_percentage = ?,
                    submitted_documents = ?
                WHERE id = ?
            ''', (
                data.get('name'), data.get('whatsapp'), data.get('gender'),
                dob_date, dob_month, dob_year,
                data.get('nationality'), data.get('email'), data.get('aadhar'), data.get('blood-group'), data.get('pan'),
                data.get('village'), data.get('taluk'), data.get('district'), data.get('religion'), data.get('caste'), data.get('category'),
                data.get('parent-name'), data.get('occupation'), data.get('postal-address'), data.get('parent-phone'),
                data.get('annual-income'), data.get('permanent-address'), pin,
                ', '.join(programs), ', '.join(languages),
                data.get('college-attended'), data.get('first-puc'), data.get('second-puc'),
                data.get('qual-exam-name'), data.get('qual-exam-reg-no'), data.get('qual-exam-year'), data.get('qual-exam-board'),
                data.get('qual-exam-marks'), data.get('qual-exam-max'), data.get('qual-exam-percent'),
                json.dumps(uploaded_docs),
                existing['id']
            ))
        else:
            # Process uploaded files for new insert
            for field_name, doc_type in DOC_MAP.items():
                if field_name in request.files:
                    file = request.files[field_name]
                    if file and file.filename != '':
                        filename = f"{app_no}_{field_name}_{secure_filename(file.filename)}"
                        file.save(os.path.join(uploads_dir, filename))
                        uploaded_docs[doc_type] = f"/static/uploads/{filename}"
            
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
                dob_date, dob_month, dob_year,
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

@app.route('/application/delete/<int:application_id>', methods=['POST'])
def delete_application(application_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Release seat if approved
        cursor.execute('SELECT status, course FROM applications WHERE id = ?', (application_id,))
        app_row = cursor.fetchone()
        if app_row:
            status = app_row['status']
            course = app_row['course']
            if status == 'approved' and course:
                cursor.execute('SELECT total_seats, filled_seats FROM course_seats WHERE course_name = ?', (course,))
                seat_row = cursor.fetchone()
                if seat_row:
                    total = seat_row['total_seats']
                    filled = seat_row['filled_seats']
                    new_filled = max(0, filled - 1)
                    new_remaining = total - new_filled
                    cursor.execute('''
                        UPDATE course_seats 
                        SET filled_seats = ?, remaining_seats = ? 
                        WHERE course_name = ?
                    ''', (new_filled, new_remaining, course))
        
        cursor.execute('DELETE FROM applications WHERE id = ?', (application_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('applications'))
    except Exception as e:
        return str(e), 500

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
