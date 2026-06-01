import os
import sqlite3
import secrets
import json
from functools import wraps
from datetime import datetime
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

ADMIN_EMAIL = os.environ.get('PRARAMBHA_ADMIN_EMAIL', 'admin@prarambha.edu.in')
ADMIN_PASSWORD_HASH = os.environ.get(
    'PRARAMBHA_ADMIN_PASSWORD_HASH',
    generate_password_hash('Admin@123')
)
def is_vercel():
    return bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))


if is_vercel():
    DATABASE_PATH = '/tmp/admissions.db'
else:
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admissions.db')

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# Specialization definitions per course (10 seats each)
SPEC_DEFINITIONS = {
    'BCA': [
        {'spec_name': 'AI & ML',        'spec_type': 'Specialisation', 'color': 'blue'},
        {'spec_name': 'Cyber Security',  'spec_type': 'Specialisation', 'color': 'indigo'},
        {'spec_name': 'Regular',         'spec_type': 'General', 'color': 'sky'},
    ],
    'BCom': [
        {'spec_name': 'Regular',         'spec_type': 'General', 'color': 'green'},
        {'spec_name': 'CA / CMA / CS',   'spec_type': 'Professional', 'color': 'teal'},
        {'spec_name': 'Tally Prime',     'spec_type': 'Specialisation', 'color': 'emerald'},
        {'spec_name': 'Data Science',    'spec_type': 'Specialisation', 'color': 'lime'},
        {'spec_name': 'SSC',             'spec_type': 'Specialisation', 'color': 'olive'},
    ],
    'BBA': [
        {'spec_name': 'LSCM',            'spec_type': 'Specialisation', 'color': 'amber'},
        {'spec_name': 'Regular',         'spec_type': 'General', 'color': 'orange'},
    ],
}

SEATS_PER_SPEC = 60


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_mapped_spec(program_string):
    if not program_string:
        return 'Regular'
    prog = program_string.lower()
    if 'artificial' in prog or 'ai' in prog:
        return 'AI & ML'
    elif 'cyber' in prog:
        return 'Cyber Security'
    elif 'logistics' in prog or 'lscm' in prog:
        return 'LSCM'
    elif 'ca/cma/cs' in prog:
        return 'CA / CMA / CS'
    elif 'tally' in prog:
        return 'Tally Prime'
    elif 'data science' in prog:
        return 'Data Science'
    elif 'staff selection' in prog or 'ssc' in prog:
        return 'SSC'
    else:
        return 'Regular'


def ensure_admin_columns():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(applications)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'status' not in columns:
        cursor.execute("ALTER TABLE applications ADD COLUMN status TEXT DEFAULT 'pending'")
    if 'admin_remark' not in columns:
        cursor.execute("ALTER TABLE applications ADD COLUMN admin_remark TEXT")

    # Defensively verify existing specialization_seats schema
    cursor.execute("PRAGMA table_info(specialization_seats)")
    spec_cols = [row[1] for row in cursor.fetchall()]
    if spec_cols and ('spec_name' not in spec_cols or 'color' not in spec_cols):
        cursor.execute("DROP TABLE specialization_seats")

    # Ensure specialization_seats table exists and is seeded
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS specialization_seats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name     TEXT NOT NULL,
            spec_name       TEXT NOT NULL,
            spec_type       TEXT NOT NULL,
            color           TEXT NOT NULL,
            total_seats     INTEGER NOT NULL DEFAULT 60,
            filled_seats    INTEGER NOT NULL DEFAULT 0,
            remaining_seats INTEGER NOT NULL DEFAULT 60,
            UNIQUE(course_name, spec_name)
        )
    ''')

    for course, specs in SPEC_DEFINITIONS.items():
        for s in specs:
            cursor.execute('''
                INSERT OR IGNORE INTO specialization_seats
                    (course_name, spec_name, spec_type, color, total_seats, filled_seats, remaining_seats)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            ''', (course, s['spec_name'], s['spec_type'], s['color'], SEATS_PER_SPEC, SEATS_PER_SPEC))

    # Force-update total_seats to current SEATS_PER_SPEC value
    cursor.execute('UPDATE specialization_seats SET total_seats = ?, remaining_seats = ? - filled_seats', (SEATS_PER_SPEC, SEATS_PER_SPEC))

    # Synchronize filled counts from actual approved applications
    cursor.execute("UPDATE specialization_seats SET filled_seats = 0, remaining_seats = total_seats")

    cursor.execute("SELECT program, course FROM applications WHERE status = 'approved'")
    approved_apps = cursor.fetchall()
    for app in approved_apps:
        prog = app['program']
        c_name = app['course'] or get_mapped_course(prog)
        spec_name = get_mapped_spec(prog)

        # Update specialization_seats
        cursor.execute('''
            UPDATE specialization_seats
            SET filled_seats = filled_seats + 1,
                remaining_seats = total_seats - (filled_seats + 1)
            WHERE course_name = ? AND spec_name = ?
        ''', (c_name, spec_name))

    # Now sync course_seats totals = sum of all its specialization seats
    for course_name in SPEC_DEFINITIONS.keys():
        row = cursor.execute(
            'SELECT COALESCE(SUM(total_seats),0) as t, COALESCE(SUM(filled_seats),0) as f FROM specialization_seats WHERE course_name = ?',
            (course_name,)
        ).fetchone()
        total_sum = row['t']
        filled_sum = row['f']
        cursor.execute('''
            UPDATE course_seats
            SET total_seats = ?, filled_seats = ?, remaining_seats = ? - ?
            WHERE course_name = ?
        ''', (total_sum, filled_sum, total_sum, filled_sum, course_name))

    conn.commit()
    conn.close()


def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']


def validate_csrf(token):
    return token and session.get('_csrf_token') == token


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin.login'))
        return view(*args, **kwargs)
    return wrapped


@admin_bp.before_request
def _ensure_admin_schema():
    """Ensure admin schema columns exist when admin routes are accessed."""
    if not hasattr(_ensure_admin_schema, '_schema_checked'):
        try:
            ensure_admin_columns()
            _ensure_admin_schema._schema_checked = True
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error ensuring admin schema: {str(e)}")
            logger.error(traceback.format_exc())
            # Mark as checked anyway to avoid retrying on every request
            _ensure_admin_schema._schema_checked = True


@admin_bp.app_context_processor
def inject_csrf_token():
    return {'csrf_token': generate_csrf_token()}


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    conn = get_db()
    total_apps = conn.execute('SELECT COUNT(*) FROM applications').fetchone()[0]
    approved = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'approved'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'rejected'").fetchone()[0]
    conn.close()
    processed = approved + rejected
    accuracy = int((processed / total_apps) * 100) if total_apps > 0 else 100

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        csrf_token = request.form.get('csrf_token')

        if not validate_csrf(csrf_token):
            flash('Invalid session token. Please refresh the page and try again.', 'danger')
            return redirect(url_for('admin.login'))

        authenticated = False
        
        # Check against database admin table first
        conn = get_db()
        db_admin = conn.execute('SELECT * FROM admin WHERE username = ?', (email,)).fetchone()
        conn.close()

        if db_admin:
            db_pwd = db_admin['password']
            if db_pwd.startswith('pbkdf2:') or db_pwd.startswith('scrypt:'):
                if check_password_hash(db_pwd, password):
                    authenticated = True
            else:
                if db_pwd == password:
                    authenticated = True

        # Fallback to default credentials from environment variables / defaults
        if not authenticated and email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            authenticated = True

        if authenticated:
            session.clear()
            session['admin_authenticated'] = True
            session['admin_email'] = email
            
            remember = request.form.get('remember') == 'on'
            if remember:
                session.permanent = True
            else:
                session.permanent = False

            resp = redirect(url_for('admin.dashboard'))
            if remember:
                resp.set_cookie('remembered_email', email, max_age=30*24*60*60)
                resp.set_cookie('remembered_password', password, max_age=30*24*60*60)
            else:
                resp.set_cookie('remembered_email', '', max_age=0)
                resp.set_cookie('remembered_password', '', max_age=0)
            return resp

        flash('Invalid email or password.', 'danger')

    email_val = request.cookies.get('remembered_email', ADMIN_EMAIL)
    pass_val = request.cookies.get('remembered_password', '')
    remember_val = request.cookies.get('remembered_email') is not None

    return render_template('admin/login.html', 
                           email=email_val, 
                           password=pass_val, 
                           remember=remember_val, 
                           total_applications=total_apps, 
                           accuracy=accuracy)


@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
def root():
    if session.get('admin_authenticated'):
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))


def get_mapped_course(program_string):
    if not program_string:
        return 'BCom'
    prog = program_string.upper()
    if 'B.C.A' in prog or 'BCA' in prog:
        return 'BCA'
    elif 'B.B.A' in prog or 'BBA' in prog:
        return 'BBA'
    else:
        return 'BCom'


def process_app_row(row):
    if row is None:
        return None
    d = dict(row)
    d['fullname'] = d.get('name')
    d['course'] = d.get('course') or get_mapped_course(d.get('program'))
    
    # Parse submitted_documents JSON
    docs = {}
    if d.get('submitted_documents'):
        try:
            docs = json.loads(d['submitted_documents'])
        except Exception:
            pass
    d['parsed_documents'] = docs
    return d


@admin_bp.route('/seats', methods=['GET', 'POST'])
@login_required
def seats():
    conn = get_db()
    
    if request.method == 'POST':
        # Handle seat update logic if they submit the update form
        # We will parse the form data and update the tables
        for key, value in request.form.items():
            if key.startswith('course_'):
                course_name = key.split('_')[1]
                new_total = int(value)
                conn.execute('UPDATE course_seats SET total_seats = ? WHERE course_name = ?', (new_total, course_name))
            elif key.startswith('spec_'):
                spec_id = int(key.split('_')[1])
                new_total = int(value)
                conn.execute('UPDATE specialization_seats SET total_seats = ? WHERE id = ?', (new_total, spec_id))
        
        conn.commit()
        flash('Seat allocations updated successfully.', 'success')
        return redirect(url_for('admin.seats'))

    course_seats = [dict(r) for r in conn.execute('SELECT * FROM course_seats').fetchall()]
    spec_seats = [dict(r) for r in conn.execute('SELECT * FROM specialization_seats ORDER BY course_name, id').fetchall()]
    conn.close()
    
    return render_template('admin/seats.html', course_seats=course_seats, spec_seats=spec_seats)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    stats = {
        'total': conn.execute('SELECT COUNT(*) FROM applications').fetchone()[0],
        'approved': conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'approved'").fetchone()[0],
        'rejected': conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'rejected'").fetchone()[0],
        'pending': conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'pending'").fetchone()[0],
    }
    
    # Process recent applications
    raw_recent = conn.execute('SELECT * FROM applications ORDER BY rowid DESC LIMIT 6').fetchall()
    recent_apps = [process_app_row(r) for r in raw_recent]
    
    # Course seats analytics
    course_seats = [dict(r) for r in conn.execute('SELECT * FROM course_seats').fetchall()]
    spec_seats = [dict(r) for r in conn.execute('SELECT * FROM specialization_seats').fetchall()]
    
    # Selected course for visual seat grid
    grid_course_raw = request.args.get('grid_course', 'BCA').strip().upper()
    if grid_course_raw == 'BCOM':
        grid_course = 'BCom'
    elif grid_course_raw in ('BCA', 'BBA'):
        grid_course = grid_course_raw
    else:
        grid_course = 'BCA'
        
    # Get total capacity for the selected course
    course_capacity = 60
    for cs in course_seats:
        if cs['course_name'] == grid_course:
            course_capacity = cs['total_seats']
            break
            
    # Get approved students for the grid
    approved_students = conn.execute('''
        SELECT id, name, approved_at 
        FROM applications 
        WHERE course = ? AND status = 'approved' 
        ORDER BY approved_at ASC
    ''', (grid_course,)).fetchall()
    
    approved_list = [dict(s) for s in approved_students]
    
    # Build visual seating grid
    seats_grid = []
    for i in range(1, course_capacity + 1):
        if i <= len(approved_list):
            student = approved_list[i - 1]
            seats_grid.append({
                'label': f'S{i}',
                'status': 'occupied',
                'student_name': student['name'],
                'student_id': student['id'],
                'approved_at': student['approved_at']
            })
        else:
            seats_grid.append({
                'label': f'S{i}',
                'status': 'available'
            })
            
    conn.close()
    return render_template(
        'admin/dashboard.html', 
        stats=stats, 
        recent_apps=recent_apps,
        course_seats=course_seats,
        spec_seats=spec_seats,
        grid_course=grid_course,
        seats_grid=seats_grid
    )


@admin_bp.route('/applications')
@login_required
def applications():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all').strip().lower()
    course_filter = request.args.get('course', 'all').strip().upper()
    page = max(1, int(request.args.get('page', 1) or 1))
    per_page = 12

    sql = 'SELECT * FROM applications'
    params = []
    conditions = []

    if status_filter != 'all':
        conditions.append('status = ?')
        params.append(status_filter)

    if course_filter != 'ALL':
        conditions.append("(course = ? OR program LIKE ? OR program LIKE ?)")
        if course_filter == 'BCA':
            params.extend(['BCA', '%BCA%', '%B.C.A.%'])
        elif course_filter == 'BBA':
            params.extend(['BBA', '%BBA%', '%B.B.A.%'])
        else:
            params.extend(['BCom', '%B.Com%', '%BCom%'])

    if search:
        conditions.append('(name LIKE ? OR email LIKE ? OR whatsapp LIKE ? OR program LIKE ? OR application_no LIKE ?)')
        like_value = f'%{search}%'
        params.extend([like_value, like_value, like_value, like_value, like_value])

    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)

    sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    conn = get_db()
    raw_apps = conn.execute(sql, params).fetchall()
    applications = [process_app_row(r) for r in raw_apps]
    
    count_sql = 'SELECT COUNT(*) FROM applications' + (' WHERE ' + ' AND '.join(conditions) if conditions else '')
    params_for_count = params[:-2] if len(params) >= 2 else []
    total = conn.execute(count_sql, params_for_count).fetchone()[0]
    
    course_seats = [dict(r) for r in conn.execute('SELECT * FROM course_seats').fetchall()]
    spec_seats = [dict(r) for r in conn.execute('SELECT * FROM specialization_seats ORDER BY course_name, id').fetchall()]
    conn.close()

    total_pages = max(1, (total + per_page - 1) // per_page)

    # Group spec_seats by course for ordered display
    grouped_specs = {}
    for course_order in ['BCA', 'BCom', 'BBA']:
        grouped_specs[course_order] = [s for s in spec_seats if s['course_name'] == course_order]

    return render_template(
        'admin/applications.html',
        applications=applications,
        search=search,
        status_filter=status_filter,
        course_filter=course_filter,
        page=page,
        total_pages=total_pages,
        total=total,
        course_seats=course_seats,
        spec_seats=spec_seats,
        grouped_specs=grouped_specs
    )

@admin_bp.route('/students')
@login_required
def students():
    search = request.args.get('search', '').strip()
    course_filter = request.args.get('course', 'all').strip().upper()
    page = max(1, int(request.args.get('page', 1) or 1))
    per_page = 12

    sql = 'SELECT * FROM applications WHERE status = "approved"'
    params = []
    conditions = []

    if course_filter != 'ALL':
        conditions.append("(course = ? OR program LIKE ? OR program LIKE ?)")
        if course_filter == 'BCA':
            params.extend(['BCA', '%BCA%', '%B.C.A.%'])
        elif course_filter == 'BBA':
            params.extend(['BBA', '%BBA%', '%B.B.A.%'])
        else:
            params.extend(['BCom', '%B.Com%', '%BCom%'])

    if search:
        conditions.append('(name LIKE ? OR email LIKE ? OR whatsapp LIKE ? OR program LIKE ? OR application_no LIKE ?)')
        like_value = f'%{search}%'
        params.extend([like_value, like_value, like_value, like_value, like_value])

    if conditions:
        sql += ' AND ' + ' AND '.join(conditions)

    sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    conn = get_db()
    raw_apps = conn.execute(sql, params).fetchall()
    students_list = [process_app_row(r) for r in raw_apps]
    
    count_sql = 'SELECT COUNT(*) FROM applications WHERE status = "approved"' + (' AND ' + ' AND '.join(conditions) if conditions else '')
    params_for_count = params[:-2] if len(params) >= 2 else []
    total = conn.execute(count_sql, params_for_count).fetchone()[0]
    
    conn.close()

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        'admin/students.html',
        students=students_list,
        search=search,
        course_filter=course_filter,
        page=page,
        total_pages=total_pages,
        total=total
    )


@admin_bp.route('/application/<int:application_id>', methods=['GET', 'POST'])
@login_required
def application_detail(application_id):
    conn = get_db()
    application_raw = conn.execute('SELECT * FROM applications WHERE id = ?', (application_id,)).fetchone()

    if application_raw is None:
        conn.close()
        abort(404)

    application = process_app_row(application_raw)
    old_status = application['status']
    course = application['course']

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf(csrf_token):
            flash('Invalid session token. Please refresh and try again.', 'danger')
            conn.close()
            return redirect(url_for('admin.application_detail', application_id=application_id))

        action = request.form.get('action')
        remark = request.form.get('admin_remark', '').strip()
        status = request.form.get('status', old_status)

        cursor = conn.cursor()

        if action == 'delete':
            if old_status == 'approved':
                # Release seat
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
            flash('Application deleted successfully and seat released.', 'success')
            return redirect(url_for('admin.applications'))

        if status not in ('pending', 'approved', 'rejected'):
            flash('Invalid status selected.', 'danger')
            conn.close()
            return redirect(url_for('admin.application_detail', application_id=application_id))

        if status == 'approved' and old_status != 'approved':
            # Check availability
            cursor.execute('SELECT total_seats, filled_seats, remaining_seats FROM course_seats WHERE course_name = ?', (course,))
            seat_row = cursor.fetchone()
            if not seat_row:
                flash(f'Course {course} seat record not found.', 'danger')
                conn.close()
                return redirect(url_for('admin.application_detail', application_id=application_id))
            
            total = seat_row['total_seats']
            filled = seat_row['filled_seats']
            remaining = seat_row['remaining_seats']

            if remaining <= 0:
                flash(f'Seats Full! Cannot approve student. No remaining seats for {course}.', 'danger')
                conn.close()
                return redirect(url_for('admin.application_detail', application_id=application_id))

            # Reserve seat
            new_filled = filled + 1
            new_remaining = total - new_filled
            cursor.execute('''
                UPDATE course_seats 
                SET filled_seats = ?, remaining_seats = ? 
                WHERE course_name = ?
            ''', (new_filled, new_remaining, course))

            approved_at_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                UPDATE applications 
                SET status = 'approved', admin_remark = ?, course = ?, approved_at = ? 
                WHERE id = ?
            ''', (remark, course, approved_at_str, application_id))
            flash(f'Admission approved! Seat reserved for course {course}.', 'success')

        elif status != 'approved' and old_status == 'approved':
            # Release seat
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

            cursor.execute('''
                UPDATE applications 
                SET status = ?, admin_remark = ?, approved_at = NULL 
                WHERE id = ?
            ''', (status, remark, application_id))
            flash(f'Admission status updated to {status}. Seat released for {course}.', 'warning')
        else:
            # Simple update
            cursor.execute('''
                UPDATE applications 
                SET status = ?, admin_remark = ? 
                WHERE id = ?
            ''', (status, remark, application_id))
            flash('Application updated successfully.', 'success')

        conn.commit()
        conn.close()
        return redirect(url_for('admin.application_detail', application_id=application_id))

    conn.close()
    return render_template('admin/application_detail.html', application=application)


@admin_bp.route('/application/<int:application_id>/action/<string:action_type>', methods=['POST'])
@login_required
def application_quick_action(application_id, action_type):
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf(csrf_token):
        flash('Invalid session token. Please try again.', 'danger')
        return redirect(request.referrer or url_for('admin.applications'))

    if action_type not in ('approve', 'reject'):
        flash('Invalid action type.', 'danger')
        return redirect(request.referrer or url_for('admin.applications'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT status, program, course FROM applications WHERE id = ?', (application_id,))
    app_row = cursor.fetchone()
    if not app_row:
        conn.close()
        abort(404)

    old_status = app_row['status']
    program = app_row['program']
    course = app_row['course'] or get_mapped_course(program)

    if action_type == 'approve':
        if old_status == 'approved':
            flash('Application is already approved.', 'info')
        else:
            # Check availability
            cursor.execute('SELECT total_seats, filled_seats, remaining_seats FROM course_seats WHERE course_name = ?', (course,))
            seat_row = cursor.fetchone()
            if not seat_row:
                flash(f'Course {course} seat record not found.', 'danger')
            else:
                total = seat_row['total_seats']
                filled = seat_row['filled_seats']
                remaining = seat_row['remaining_seats']

                if remaining <= 0:
                    flash(f'Seats Full! Cannot approve student. No remaining seats for {course}.', 'danger')
                else:
                    new_filled = filled + 1
                    new_remaining = total - new_filled
                    cursor.execute('''
                        UPDATE course_seats 
                        SET filled_seats = ?, remaining_seats = ? 
                        WHERE course_name = ?
                    ''', (new_filled, new_remaining, course))

                    approved_at_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute('''
                        UPDATE applications 
                        SET status = 'approved', course = ?, approved_at = ? 
                        WHERE id = ?
                    ''', (course, approved_at_str, application_id))
                    flash(f'Application approved! Seat reserved for {course}.', 'success')

    elif action_type == 'reject':
        if old_status == 'rejected':
            flash('Application is already rejected.', 'info')
        else:
            if old_status == 'approved':
                # Release seat
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

            cursor.execute('''
                UPDATE applications 
                SET status = 'rejected', approved_at = NULL 
                WHERE id = ?
            ''', (application_id,))
            flash('Application rejected and seat released.', 'warning')

    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('admin.applications'))


# ── Specialization Seat API ────────────────────────────────────────────────
@admin_bp.route('/api/spec-seats/<course>/<path:spec_name>')
@login_required
def api_spec_seats(course, spec_name):
    """Return JSON with seat-level detail for a given course + specialization."""
    conn = get_db()

    # Fetch the spec row
    row = conn.execute(
        'SELECT * FROM specialization_seats WHERE course_name = ? AND spec_name = ?',
        (course, spec_name)
    ).fetchone()

    if not row:
        conn.close()
        return {'error': 'Specialization not found'}, 404

    total    = row['total_seats']
    filled   = row['filled_seats']
    remaining = row['remaining_seats']

    # Get approved students for this specialization using get_mapped_spec on their program string
    all_approved = conn.execute('''
        SELECT id, name, approved_at, application_no, program
        FROM applications 
        WHERE course = ? AND status = 'approved'
        ORDER BY approved_at ASC
    ''', (course,)).fetchall()

    approved_list = []
    for s in all_approved:
        if get_mapped_spec(s['program']) == spec_name:
            approved_list.append(dict(s))

    # Build individual seat list (S1 … S{total})
    seats = []
    for i in range(1, total + 1):
        if i <= len(approved_list):
            student = approved_list[i - 1]
            seats.append({
                'label': f'S{i}',
                'status': 'occupied',
                'student_name': student['name'],
                'student_id': student['id'],
                'application_no': student['application_no'] or f'APP-{student["id"]}',
                'approved_at': student['approved_at']
            })
        else:
            seats.append({
                'label': f'S{i}',
                'status': 'available'
            })

    conn.close()
    return {
        'course':    course,
        'spec_name': spec_name,
        'spec_type': row['spec_type'],
        'total':     total,
        'filled':    filled,
        'remaining': remaining,
        'seats':     seats
    }


@admin_bp.route('/course/<course>/<path:spec_name>')
@login_required
def course_spec_detail(course, spec_name):
    """Full-page seat allocation view for a specific course specialization."""
    conn = get_db()

    # Fetch spec row
    spec_row = conn.execute(
        'SELECT * FROM specialization_seats WHERE course_name = ? AND spec_name = ?',
        (course, spec_name)
    ).fetchone()

    if not spec_row:
        conn.close()
        abort(404)

    total = spec_row['total_seats']
    spec_type = spec_row['spec_type']
    color = spec_row['color']

    # Get approved students for this course + spec
    all_approved = conn.execute('''
        SELECT id, name, approved_at, application_no, program
        FROM applications
        WHERE course = ? AND status = 'approved'
        ORDER BY approved_at ASC
    ''', (course,)).fetchall()

    approved_list = []
    for s in all_approved:
        if get_mapped_spec(s['program']) == spec_name:
            approved_list.append(dict(s))

    # Build 60-seat grid
    seats = []
    for i in range(1, total + 1):
        if i <= len(approved_list):
            student = approved_list[i - 1]
            seats.append({
                'label': f'S{i}',
                'status': 'occupied',
                'student_name': student['name'],
                'student_id': student['id'],
                'application_no': student['application_no'] or f'APP-{student["id"]}',
                'approved_at': student['approved_at']
            })
        else:
            seats.append({
                'label': f'S{i}',
                'status': 'available'
            })

    filled = len(approved_list)
    remaining = total - filled

    # Fetch course_seats for the breadcrumb totals
    course_seats = [dict(r) for r in conn.execute('SELECT * FROM course_seats').fetchall()]
    spec_seats = [dict(r) for r in conn.execute('SELECT * FROM specialization_seats WHERE course_name = ?', (course,)).fetchall()]

    conn.close()
    return render_template(
        'admin/course_spec_detail.html',
        course=course,
        spec_name=spec_name,
        spec_type=spec_type,
        color=color,
        total=total,
        filled=filled,
        remaining=remaining,
        seats=seats,
        course_seats=course_seats,
        spec_seats=spec_seats
    )




@admin_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    current_email = session.get('admin_email')
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        csrf_token = request.form.get('csrf_token')

        if not validate_csrf(csrf_token):
            flash('Invalid session token. Please try again.', 'danger')
            return redirect(url_for('admin.profile'))

        if not email:
            flash('Email cannot be empty.', 'danger')
            return redirect(url_for('admin.profile'))

        # Retrieve current credentials from DB to verify the password
        conn = get_db()
        db_admin = conn.execute('SELECT * FROM admin WHERE username = ?', (current_email,)).fetchone()
        
        pwd_verified = False
        if db_admin:
            db_pwd = db_admin['password']
            if db_pwd.startswith('pbkdf2:') or db_pwd.startswith('scrypt:'):
                if check_password_hash(db_pwd, current_password):
                    pwd_verified = True
            else:
                if db_pwd == current_password:
                    pwd_verified = True
        else:
            # Fallback check
            if current_email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, current_password):
                pwd_verified = True

        if not pwd_verified:
            conn.close()
            flash('Verification failed: Incorrect current password.', 'danger')
            return redirect(url_for('admin.profile'))

        # If changing password, validate
        updated_password_hash = None
        if new_password:
            if new_password != confirm_password:
                conn.close()
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('admin.profile'))
            updated_password_hash = generate_password_hash(new_password)

        # Update db
        cursor = conn.cursor()
        if db_admin:
            if updated_password_hash:
                cursor.execute('UPDATE admin SET username = ?, password = ? WHERE id = ?', (email, updated_password_hash, db_admin['id']))
            else:
                cursor.execute('UPDATE admin SET username = ? WHERE id = ?', (email, db_admin['id']))
        else:
            pwd_to_save = updated_password_hash if updated_password_hash else ADMIN_PASSWORD_HASH
            cursor.execute('INSERT INTO admin (username, password) VALUES (?, ?)', (email, pwd_to_save))

        conn.commit()
        conn.close()

        # Update session
        session['admin_email'] = email
        flash('Profile settings updated successfully.', 'success')
        return redirect(url_for('admin.profile'))

    return render_template('admin/profile.html', email=current_email)


