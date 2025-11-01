import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "hospital.db"

def connect_to_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def create_tables():
    conn = connect_to_db()
    cur = conn.cursor()

    # Admin (Hospital Staff)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    """)

    # Department / Specialization
    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    );
    """)

    # Doctor
    cur.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department_id INTEGER,
        email TEXT UNIQUE,
        phone TEXT,
        password TEXT,
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
    );
    """)

    # Patient
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        age INTEGER,
        gender TEXT,
        password TEXT
    );
    """)

    # Appointment
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Booked', 'Completed', 'Cancelled')),
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
    );
    """)

    # Treatment
    cur.execute("""
    CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        diagnosis TEXT,
        prescription TEXT,
        notes TEXT,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def create_default_admin(username="admin", password="password1729"):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM admins;")
    row = cur.fetchone()

    if row and row["cnt"] == 0:
        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO admins (username, password) VALUES (?, ?);", (username, hashed))
        conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    create_default_admin()
