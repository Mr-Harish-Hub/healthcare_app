# app.py
from flask import Flask, render_template, request, redirect, session, flash
from models.database import init_db, get_db

app = Flask(__name__)
app.secret_key = "unique_super_secret_key_2025"

# initialize DB
init_db()

@app.route('/')
def root():
    return redirect('/home')

@app.route('/home')
def landing():
    return render_template("landing.html")

# ---------------- Admin ----------------
@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        pwd = request.form.get('password','')
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM admins WHERE email=?", (email,))
        admin = cur.fetchone()
        db.close()
        if not admin:
            flash("Email not found", "danger")
            return redirect('/login')
        if admin['password'] != pwd:
            flash("Incorrect password", "danger")
            return redirect('/login')
        session['admin'] = admin['name']
        flash("Logged in", "success")
        return redirect('/admin/dashboard')
    return render_template("admin_login.html")

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) cnt FROM doctors")
    docs = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) cnt FROM patients")
    pats = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) cnt FROM appointments")
    appt = cur.fetchone()['cnt']
    # recent simple activity: last 8 appointments (as sample)
    cur.execute("""
        SELECT a.id AS id, p.name as p_name, d.name as d_name, a.date, a.time
        FROM appointments a
        LEFT JOIN patients p ON p.id = a.patient_id
        LEFT JOIN doctors d ON d.id = a.doctor_id
        ORDER BY a.id DESC LIMIT 8
    """)
    recent = cur.fetchall()
    db.close()
    stats = {'doctors': docs, 'patients': pats, 'appointments': appt}
    # convert recent to simpler structure
    recent_list = []
    for r in recent:
        recent_list.append({'type':'appointment','summary': f"{r['p_name'] or 'Unknown'} -> {r['d_name'] or 'Unknown'}", 'at': f"{r['date']} {r['time']}"})
    return render_template("admin/admin_dashboard.html", admin=session['admin'], stats=stats, recent=recent_list)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect('/home')

# Admin add doctor
@app.route('/admin/add-doctor', methods=['GET','POST'])
def add_doctor():
    if 'admin' not in session:
        return redirect('/login')
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        specialization = request.form.get('specialization','').strip()
        availability = request.form.get('availability','').strip()
        password = request.form.get('password','')
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO doctors (name, specialization, availability, password) VALUES (?, ?, ?, ?)",
                    (name, specialization, availability, password))
        db.commit()
        db.close()
        flash("Doctor added", "success")
        return redirect('/admin/view-doctors')
    return render_template("admin/add_doctor.html")

@app.route('/admin/view-doctors')
def view_doctors():
    if 'admin' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, specialization, availability FROM doctors ORDER BY id DESC")
    doctors = cur.fetchall()
    db.close()
    return render_template("admin/view_doctors.html", doctors=doctors)

@app.route('/admin/delete-doctor/<int:doc_id>')
def delete_doctor(doc_id):
    if 'admin' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM doctors WHERE id=?", (doc_id,))
    cur.execute("DELETE FROM doctor_slots WHERE doctor_id=?", (doc_id,))
    cur.execute("DELETE FROM appointments WHERE doctor_id=?", (doc_id,))
    db.commit()
    db.close()
    flash("Doctor removed", "info")
    return redirect('/admin/view-doctors')

@app.route('/admin/registered-patients')
def registered_patients():
    if 'admin' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, email, contact FROM patients ORDER BY id DESC")
    patients = cur.fetchall()
    db.close()
    return render_template("admin/registered_patients.html", patients=patients)

@app.route('/admin/patient-history/<int:patient_id>')
def admin_patient_history(patient_id):
    if 'admin' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM patients WHERE id=?", (patient_id,))
    patient = cur.fetchone()
    cur.execute("""
        SELECT a.*, d.name as doctor_name
        FROM appointments a
        LEFT JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id=?
        ORDER BY a.id DESC
    """, (patient_id,))
    history = cur.fetchall()
    db.close()
    return render_template("admin/patient_history.html", patient=patient, history=history)

@app.route('/admin/search', methods=['GET','POST'])
def admin_search():
    if 'admin' not in session:
        return redirect('/login')
    q = ""
    results = {'patients': [], 'doctors': []}
    if request.method == 'POST':
        q = request.form.get('q','').strip()
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id, name, email FROM patients WHERE name LIKE ? OR email LIKE ? ORDER BY id DESC", (f"%{q}%", f"%{q}%"))
        results['patients'] = cur.fetchall()
        cur.execute("SELECT id, name, specialization FROM doctors WHERE name LIKE ? OR specialization LIKE ? ORDER BY id DESC", (f"%{q}%", f"%{q}%"))
        results['doctors'] = cur.fetchall()
        db.close()
    return render_template("admin/search.html", query=q, results=results)

@app.route('/admin/view-appointments')
def admin_view_appointments():
    if 'admin' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.id, p.name as patient_name, d.name as doctor_name, a.date, a.time, a.status
        FROM appointments a
        LEFT JOIN patients p ON p.id = a.patient_id
        LEFT JOIN doctors d ON d.id = a.doctor_id
        ORDER BY a.id DESC
    """)
    appointments = cur.fetchall()
    db.close()
    return render_template("admin/view_appointments.html", appointments=appointments)

@app.route('/admin/doctor-availability/<int:doctor_id>')
def admin_doctor_availability(doctor_id):
    if 'admin' not in session:
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM doctor_slots WHERE doctor_id=? ORDER BY day, time_range", (doctor_id,))
    slots = cur.fetchall()
    db.close()
    return render_template("admin/doctor_availability.html", slots=slots)

# ---------------- Patient ----------------
@app.route('/patient/register', methods=['GET','POST'])
def patient_register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        contact = request.form.get('contact','').strip()
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM patients WHERE email=?", (email,))
        if cur.fetchone():
            db.close()
            flash("Email already registered", "danger")
            return redirect('/patient/register')
        cur.execute("INSERT INTO patients (name, email, password, contact) VALUES (?, ?, ?, ?)",
                    (name, email, password, contact))
        db.commit()
        db.close()
        flash("Registered successfully", "success")
        return redirect('/patient/login')
    return render_template("patient/register.html")

@app.route('/patient/login', methods=['GET','POST'])
def patient_login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM patients WHERE email=?", (email,))
        p = cur.fetchone()
        db.close()
        if not p:
            flash("Email not found", "danger")
            return redirect('/patient/login')
        if p['password'] != password:
            flash("Incorrect password", "danger")
            return redirect('/patient/login')
        session['patient'] = p['id']
        session['patient_name'] = p['name']
        flash("Logged in", "success")
        return redirect('/patient/dashboard')
    return render_template("patient/login.html")

@app.route('/patient/dashboard')
def patient_dashboard():
    if 'patient' not in session:
        return redirect('/patient/login')
    return render_template("patient/dashboard.html", patient=session.get('patient_name'))

@app.route('/patient/book', methods=['GET','POST'])
def patient_book():
    if 'patient' not in session:
        return redirect('/patient/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, specialization FROM doctors ORDER BY id DESC")
    doctors = cur.fetchall()
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        date = request.form.get('date')
        time = request.form.get('time')
        cur.execute("INSERT INTO appointments (doctor_id, patient_id, date, time) VALUES (?, ?, ?, ?)",
                    (doctor_id, session['patient'], date, time))
        db.commit()
        db.close()
        flash("Appointment booked", "success")
        return redirect('/patient/history')
    db.close()
    return render_template("patient/book.html", doctors=doctors)

@app.route('/patient/history')
def patient_history():
    if 'patient' not in session:
        return redirect('/patient/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, d.name as doctor_name
        FROM appointments a
        LEFT JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id=?
        ORDER BY a.id DESC
    """, (session['patient'],))
    history = cur.fetchall()
    db.close()
    return render_template("patient/history.html", history=history)

@app.route('/patient/availability/<int:doctor_id>')
def patient_check_availability(doctor_id):
    if 'patient' not in session:
        return redirect('/patient/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM doctor_slots WHERE doctor_id=? AND is_booked=0 ORDER BY day, time_range", (doctor_id,))
    slots = cur.fetchall()
    db.close()
    return render_template("patient/check_availability.html", slots=slots, doctor_id=doctor_id)

@app.route('/patient/book-slot/<int:slot_id>')
def patient_book_slot(slot_id):
    if 'patient' not in session:
        return redirect('/patient/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM doctor_slots WHERE id=? AND is_booked=0", (slot_id,))
    slot = cur.fetchone()
    if not slot:
        db.close()
        flash("Slot unavailable", "danger")
        return redirect('/patient/dashboard')
    cur.execute("INSERT INTO appointments (doctor_id, patient_id, date, time) VALUES (?, ?, ?, ?)",
                (slot['doctor_id'], session['patient'], slot['day'], slot['time_range']))
    cur.execute("UPDATE doctor_slots SET is_booked=1 WHERE id=?", (slot_id,))
    db.commit()
    db.close()
    flash("Slot booked", "success")
    return redirect('/patient/history')

# ---------------- Doctor ----------------
@app.route('/doctor/login', methods=['GET','POST'])
def doctor_login():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        password = request.form.get('password','')
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM doctors WHERE name=?", (name,))
        d = cur.fetchone()
        db.close()
        if not d:
            flash("Doctor not found", "danger")
            return redirect('/doctor/login')
        if d['password'] != password:
            flash("Incorrect password", "danger")
            return redirect('/doctor/login')
        session['doctor'] = d['id']
        session['doctor_name'] = d['name']
        flash("Signed in", "success")
        return redirect('/doctor/dashboard')
    return render_template("doctor/login.html")

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'doctor' not in session:
        return redirect('/doctor/login')
    return render_template("doctor/dashboard.html", doctor=session.get('doctor_name'))

@app.route('/doctor/appointments')
def doctor_appointments():
    if 'doctor' not in session:
        return redirect('/doctor/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, p.name as patient_name
        FROM appointments a
        LEFT JOIN patients p ON p.id = a.patient_id
        WHERE a.doctor_id=?
        ORDER BY a.id DESC
    """, (session['doctor'],))
    appointments = cur.fetchall()
    db.close()
    return render_template("doctor/appointments.html", appointments=appointments)

@app.route('/doctor/update/<int:appointment_id>', methods=['GET','POST'])
def doctor_update(appointment_id):
    if 'doctor' not in session:
        return redirect('/doctor/login')
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        status = request.form.get('status','Booked')
        diagnosis = request.form.get('diagnosis','')
        prescription = request.form.get('prescription','')
        cur.execute("UPDATE appointments SET status=?, diagnosis=?, prescriptions=? WHERE id=?",
                    (status, diagnosis, prescription, appointment_id))
        db.commit()
        db.close()
        flash("Appointment updated", "success")
        return redirect('/doctor/appointments')
    cur.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,))
    appointment = cur.fetchone()
    db.close()
    return render_template("doctor/update.html", appointment=appointment)

@app.route('/doctor/availability', methods=['GET','POST'])
def doctor_availability():
    if 'doctor' not in session:
        return redirect('/doctor/login')
    if request.method == 'POST':
        day = request.form.get('date')
        times = request.form.getlist('time_slots')
        db = get_db()
        cur = db.cursor()
        for t in times:
            cur.execute("INSERT INTO doctor_slots (doctor_id, day, time_range) VALUES (?, ?, ?)",
                        (session['doctor'], day, t))
        db.commit()
        db.close()
        flash("Availability saved", "success")
        return redirect('/doctor/availability')
    return render_template("doctor/add_availability.html")

if __name__ == "__main__":
    app.run(debug=True)
