from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "att_sys_secret_xK9#mP2!vQ8")

# --- Configuration ---
DATABASE = 'attendance.db'
HARDWARE_API_KEY = "unipr_hardware_key_2026"

# Email Configuration (Update with real credentials for production)
EMAIL_SENDER = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        with app.app_context():
            db = get_db()
            with open('init_db.sql', 'r') as f:
                db.cursor().executescript(f.read())
            
            # Create a default admin
            admin_pass = generate_password_hash("admin123")
            db.execute("INSERT OR IGNORE INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                       ("admin", admin_pass, "admin", "System Administrator"))
            db.commit()
            print("Database initialized successfully.")

# --- Background Email Tasks ---
def send_email_async(to_email, subject, body):
    def send():
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Failed to send email: {e}")

    thread = threading.Thread(target=send)
    thread.start()

# --- Auth Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            session['role'] = user['role']
            session['name'] = user['full_name']
            session['user_id'] = user['id']
            flash("Logged in successfully!", "success")
            return redirect(url_for('dashboard'))
        
        flash("Invalid username or password", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Dashboard & Core Logic ---
@app.route('/')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') == 'student':
        return redirect(url_for('student_portal'))

    db = get_db()
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    today_date = datetime.now().strftime('%Y-%m-%d')
    present_today = db.execute("SELECT COUNT(DISTINCT student_id) FROM attendance WHERE record_date = ? AND status = 'Present'", (today_date,)).fetchone()[0]
    pending_leaves = db.execute("SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'").fetchone()[0]
    
    recent_activity = db.execute("""
        SELECT a.*, s.full_name, sub.name as subject_name 
        FROM attendance a 
        JOIN students s ON a.student_id = s.student_id 
        JOIN subjects sub ON a.subject_id = sub.id
        ORDER BY a.id DESC LIMIT 5
    """).fetchall()

    return render_template('dashboard.html', 
                         total_students=total_students, 
                         present_today=present_today,
                         pending_leaves=pending_leaves,
                         recent_activity=recent_activity)

# --- Student Management ---
@app.route('/students')
def student_list():
    if 'user' not in session or session.get('role') == 'student':
        return redirect(url_for('login'))
    
    db = get_db()
    students = db.execute("SELECT * FROM students ORDER BY student_id ASC").fetchall()
    return render_template('student_list.html', students=students)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        sid = request.form['student_id']
        name = request.form['full_name']
        dept = request.form['department']
        email = request.form['email']
        phone = request.form['phone']
        
        db = get_db()
        try:
            db.execute("INSERT INTO students (student_id, full_name, department, email, phone) VALUES (?, ?, ?, ?, ?)",
                       (sid, name, dept, email, phone))
            
            # Create a student user account automatically
            hashed_pass = generate_password_hash(sid) # Default password is ID
            db.execute("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
                       (sid, hashed_pass, 'student', name))
            
            db.commit()
            flash("Student added successfully. Default password is their ID.", "success")
            return redirect(url_for('student_list'))
        except sqlite3.IntegrityError:
            flash("Error: Student ID or Email already exists.", "danger")
            
    return render_template('add_student.html')

@app.route('/students/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?", (id,)).fetchone()

    if request.method == 'POST':
        name = request.form['full_name']
        dept = request.form['department']
        email = request.form['email']
        phone = request.form['phone']
        
        db.execute("UPDATE students SET full_name=?, department=?, email=?, phone=? WHERE id=?",
                   (name, dept, email, phone, id))
        db.commit()
        flash("Student updated.", "success")
        return redirect(url_for('student_list'))
        
    return render_template('edit_student.html', student=student)

@app.route('/students/profile/<string:sid>')
def student_profile(sid):
    if 'user' not in session: return redirect(url_for('login'))
    
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE student_id = ?", (sid,)).fetchone()
    
    # Calculate detailed stats
    total_days = db.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (sid,)).fetchone()[0]
    present_days = db.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'Present'", (sid,)).fetchone()[0]
    absent_days = total_days - present_days
    pct = round((present_days / total_days * 100), 1) if total_days > 0 else 0
    
    records = db.execute("""
        SELECT a.*, s.name as subject_name 
        FROM attendance a 
        JOIN subjects s ON a.subject_id = s.id 
        WHERE a.student_id = ? ORDER BY a.record_date DESC LIMIT 20
    """, (sid,)).fetchall()

    return render_template('student_profile.html', student=student, pct=pct, present=present_days, absent=absent_days, records=records)

# --- Attendance Marking ---
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'user' not in session or session.get('role') == 'student':
        return redirect(url_for('login'))
    
    db = get_db()
    subjects = db.execute("SELECT * FROM subjects").fetchall()
    students = db.execute("SELECT * FROM students ORDER BY student_id ASC").fetchall()
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        date = request.form.get('date')
        
        # Check if already marked
        exists = db.execute("SELECT 1 FROM attendance WHERE subject_id = ? AND record_date = ?", (subject_id, date)).fetchone()
        if exists:
            flash("Attendance for this subject and date has already been recorded.", "warning")
            return redirect(url_for('attendance'))

        for s in students:
            status = request.form.get(f"status_{s['student_id']}", "Absent")
            db.execute("INSERT INTO attendance (student_id, subject_id, record_date, status) VALUES (?, ?, ?, ?)",
                       (s['student_id'], subject_id, date, status))
        
        db.commit()
        flash("Attendance recorded successfully.", "success")
        return redirect(url_for('attendance_history'))

    return render_template('attendance.html', subjects=subjects, students=students)

@app.route('/history')
def attendance_history():
    if 'user' not in session or session.get('role') == 'student':
        return redirect(url_for('login'))
    
    db = get_db()
    history = db.execute("""
        SELECT a.record_date, a.subject_id, s.name as subject_name, 
               COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        GROUP BY a.record_date, a.subject_id
        ORDER BY a.record_date DESC
    """).fetchall()
    return render_template('attendance_history.html', history=history)

@app.route('/history/detail/<string:date>/<int:sub_id>')
def attendance_detail(date, sub_id):
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    subject = db.execute("SELECT name FROM subjects WHERE id = ?", (sub_id,)).fetchone()
    records = db.execute("""
        SELECT a.*, s.full_name 
        FROM attendance a 
        JOIN students s ON a.student_id = s.student_id 
        WHERE a.record_date = ? AND a.subject_id = ?
    """, (date, sub_id)).fetchall()
    return render_template('attendance_detail.html', records=records, date=date, subject=subject['name'])

# --- Reporting ---
@app.route('/reports')
def report():
    if 'user' not in session or session.get('role') == 'student':
        return redirect(url_for('login'))
    
    db = get_db()
    # Logic: Get average percentage for every student
    stats = db.execute("""
        SELECT s.student_id, s.full_name, s.department,
               COUNT(a.id) as total_classes,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present_count
        FROM students s
        LEFT JOIN attendance a ON s.student_id = a.student_id
        GROUP BY s.student_id
    """).fetchall()
    
    report_data = []
    for row in stats:
        pct = round((row['present_count'] / row['total_classes'] * 100), 1) if row['total_classes'] > 0 else 0
        report_data.append({
            'id': row['student_id'],
            'name': row['full_name'],
            'dept': row['department'],
            'total': row['total_classes'],
            'present': row['present_count'],
            'pct': pct
        })
        
    return render_template('report.html', data=report_data)

# --- Hardware API ---
@app.route('/api/hardware/scan', methods=['POST'])
def hardware_scan():
    data = request.json
    if not data or data.get('api_key') != HARDWARE_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    student_id = data.get('student_id')
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    # Check if a subject is currently active (Simple logic: mark for first subject if not specified)
    # In a real system, you'd match based on time/timetable
    subject = db.execute("SELECT id FROM subjects LIMIT 1").fetchone()
    if not subject:
        return jsonify({"error": "No subjects configured"}), 400
        
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Prevent double scanning for same subject/day
    exists = db.execute("SELECT id FROM attendance WHERE student_id = ? AND subject_id = ? AND record_date = ?",
                       (student_id, subject['id'], today)).fetchone()
    
    if exists:
        return jsonify({"success": True, "status": "Ignored (Already scanned today)"}), 200

    db.execute("INSERT INTO attendance (student_id, subject_id, record_date, status) VALUES (?, ?, ?, 'Present')",
               (student_id, subject['id'], today))
    db.commit()
    
    return jsonify({"success": True, "message": f"Attendance recorded for {student['full_name']}", "status": "Present"}), 200

# --- Admin & Staff Management ---
@app.route('/staff', methods=['GET', 'POST'])
def manage_staff():
    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('dashboard'))
    
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form['username']
            password = generate_password_hash(request.form['password'])
            name = request.form['full_name']
            designation = request.form.get('designation')
            sector = request.form.get('sector')
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            try:
                db.execute("""INSERT INTO users 
                    (username, password, role, full_name, designation, sector, email, phone) 
                    VALUES (?, ?, 'teacher', ?, ?, ?, ?, ?)""",
                    (username, password, name, designation, sector, email, phone))
                db.commit()
                flash("Teacher account created.", "success")
            except:
                flash("Username already exists.", "danger")
        
        elif action == 'delete':
            sid = request.form.get('staff_id')
            db.execute("DELETE FROM users WHERE id = ?", (sid,))
            db.commit()
            flash("Staff access revoked.", "warning")

    staff_list = db.execute("SELECT * FROM users WHERE role = 'teacher'").fetchall()
    return render_template('staff.html', staff_list=staff_list)

@app.route('/subjects', methods=['GET', 'POST'])
def manage_subjects():
    if session.get('role') != 'admin': return redirect(url_for('dashboard'))
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        db.execute("INSERT INTO subjects (name, code) VALUES (?, ?)", (name, code))
        db.commit()
        flash("Subject added.", "success")
    
    subs = db.execute("SELECT * FROM subjects").fetchall()
    return render_template('subjects.html', subjects=subs)

@app.route('/profile', methods=['GET', 'POST'])
def admin_profile():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (session['user'],)).fetchone()
    
    if request.method == 'POST':
        # Update settings
        new_name = request.form['full_name']
        new_email = request.form['email']
        db.execute("UPDATE users SET full_name = ?, email = ? WHERE id = ?", (new_name, new_email, user['id']))
        db.commit()
        session['name'] = new_name
        flash("Profile updated.", "success")
        return redirect(url_for('admin_profile'))
        
    return render_template('admin_profile.html', user=user)

# --- Student Portal ---
@app.route('/portal')
def student_portal():
    if 'user' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    sid = session['user']
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE student_id = ?", (sid,)).fetchone()
    
    # Stats
    total = db.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (sid,)).fetchone()[0]
    present = db.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'Present'", (sid,)).fetchone()[0]
    att_pct = round((present/total*100), 1) if total > 0 else 0
    
    records = db.execute("""
        SELECT a.*, s.name as subject_name 
        FROM attendance a 
        JOIN subjects s ON a.subject_id = s.id 
        WHERE a.student_id = ? ORDER BY a.record_date DESC LIMIT 5
    """, (sid,)).fetchall()
    
    notices = db.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 3").fetchall()
    my_leaves = db.execute("SELECT * FROM leave_requests WHERE student_id = ? ORDER BY id DESC", (sid,)).fetchall()
    
    return render_template('student_portal.html', 
                         student=student, 
                         att_pct=att_pct, 
                         hw_pct=85, # Mock data for assignments
                         records=records,
                         notices=notices,
                         my_leaves=my_leaves)

# --- Leave Management ---
@app.route('/leaves', methods=['GET', 'POST'])
def manage_leaves():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    
    if request.method == 'POST':
        if session.get('role') == 'student':
            # Student submitting leave
            start = request.form['start_date']
            end = request.form['end_date']
            reason = request.form['reason']
            db.execute("INSERT INTO leave_requests (student_id, start_date, end_date, reason) VALUES (?, ?, ?, ?)",
                       (session['user'], start, end, reason))
            db.commit()
            flash("Leave request submitted for review.", "success")
            return redirect(url_for('student_portal'))
        else:
            # Teacher/Admin processing leave
            lid = request.form['leave_id']
            action = request.form['action']
            db.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (action, lid))
            db.commit()
            flash(f"Leave request {action}.", "success")
            
    leaves = db.execute("""
        SELECT l.*, s.full_name, s.department 
        FROM leave_requests l 
        JOIN students s ON l.student_id = s.student_id 
        ORDER BY l.id DESC
    """).fetchall()
    return render_template('leaves.html', leaves=leaves)

# --- Noticeboard ---
@app.route('/notices', methods=['GET', 'POST'])
def manage_notices():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    
    if request.method == 'POST' and session.get('role') == 'admin':
        action = request.form.get('action')
        if action == 'add':
            title = request.form['title']
            msg = request.form['message']
            db.execute("INSERT INTO notices (title, message, author) VALUES (?, ?, ?)",
                       (title, msg, session.get('name', 'Admin')))
            db.commit()
            flash("Notice published.", "success")
        elif action == 'delete':
            nid = request.form['notice_id']
            db.execute("DELETE FROM notices WHERE id = ?", (nid,))
            db.commit()
            flash("Notice removed.", "info")

    notices = db.execute("SELECT * FROM notices ORDER BY id DESC").fetchall()
    return render_template('notices.html', notices=notices)

@app.route('/send-notice', methods=['POST'])
def send_notice():
    if session.get('role') not in ['admin', 'teacher']:
        return redirect(url_for('dashboard'))
        
    to_email = request.form['to_email']
    subject = request.form['subject']
    message = request.form['message']
    
    html_body = f"""
    <div style='font-family: Arial; padding: 20px; border: 1px solid #eee;'>
        <h2 style='color: #1e3a8a;'>Institutional Notice</h2>
        <p>{message}</p>
        <hr>
        <small>Sent by {session.get('name')} via CPI Attendance Portal</small>
    </div>
    """
    
    send_email_async(to_email, subject, html_body)
    flash(f"Email notification sent to {to_email}", "success")
    return redirect(request.form.get('redirect_url', url_for('dashboard')))

# --- Hardware Monitor ---
@app.route('/hardware-monitor')
def hardware_monitor():
    if session.get('role') != 'admin': return redirect(url_for('dashboard'))
    # In a real app, you'd log these to a DB table. Here we mock some recent activity.
    mock_logs = [
        {"scan_time": "2026-05-03 09:15:02", "student_id": "STU-001", "status": "Success"},
        {"scan_time": "2026-05-03 09:16:45", "student_id": "STU-002", "status": "Success"},
        {"scan_time": "2026-05-03 09:18:10", "student_id": "STU-999", "status": "Failed (Not Found)"},
    ]
    return render_template('hardware.html', logs=mock_logs)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
