import sqlite3
import pandas as pd
import bcrypt
import io
from datetime import datetime
import zipfile
import os




class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """Returns a connection object to the SQLite database."""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        """Initializes schema and auto-migrates existing tables to add missing columns."""
        with self._get_connection() as conn:
            # 1. Users Table
            conn.execute('''CREATE TABLE IF NOT EXISTS users 
                (student_id TEXT PRIMARY KEY, 
                 password BLOB, 
                 role TEXT, 
                 name TEXT)''')
            
            # 2. Activities Table
            conn.execute('''CREATE TABLE IF NOT EXISTS activities 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 student_id TEXT, 
                 title TEXT, 
                 summary TEXT, 
                 skills TEXT, 
                 date TEXT, 
                 file_path TEXT,
                 grade_section TEXT,
                 status TEXT DEFAULT 'pending')''')
            
            # 3. Grades Table
            conn.execute('''CREATE TABLE IF NOT EXISTS grades 
                (student_id TEXT, 
                 year INTEGER, 
                 term TEXT, 
                 subject TEXT, 
                 mark INTEGER)''')

            # 4. AUTO-MIGRATION LOGIC
            # This automatically fixes the "no such column" error by checking current structure
            cursor = conn.execute("PRAGMA table_info(activities)")
            columns = [column[1] for column in cursor.fetchall()]
            
            migrations = [
                ('status', "TEXT DEFAULT 'pending'"),
                ('grade_section', "TEXT"),
                ('file_path', "TEXT")
            ]
            
            for col_name, col_type in migrations:
                if col_name not in columns:
                    conn.execute(f"ALTER TABLE activities ADD COLUMN {col_name} {col_type}")
            
            # 5. Default Admin Creation (admin / admin123)
            admin_check = conn.execute("SELECT * FROM users WHERE role='Admin'").fetchone()
            if not admin_check:
                hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
                conn.execute("INSERT INTO users VALUES (?,?,?,?)", ("admin", hashed, "Admin", "System Administrator"))
            
            conn.commit()

    # --- AUTHENTICATION ---
    def verify_login(self, sid, pwd):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            user = conn.execute("SELECT * FROM users WHERE student_id=?", (sid,)).fetchone()
            if user and bcrypt.checkpw(pwd.encode(), user['password']):
                return user
        return None

    def create_user(self, sid, name, password, role="Student"):
        """Creates a new user with a hashed password."""
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        try:
            with self._get_connection() as conn:
                conn.execute("INSERT INTO users (student_id, password, role, name) VALUES (?,?,?,?)", 
                             (sid, hashed, role, name))
                conn.commit()
            return True, "User created successfully!"
        except sqlite3.IntegrityError:
            return False, "User ID already exists."

    def reset_password(self, sid, new_password):
        """Updates a user's password with a new hashed version."""
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE users SET password=? WHERE student_id=?", 
                             (hashed, sid))
                conn.commit()
            return True, f"Password for {sid} has been reset."
        except Exception as e:
            return False, str(e)

    # --- PORTFOLIO & APPROVAL ---
    def save_activity(self, sid, title, summary, skills, path=None, status='pending'):
        """Saves project to portfolio."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            conn.execute('''INSERT INTO activities (student_id, title, summary, skills, date, file_path, status) 
                            VALUES (?,?,?,?,?,?,?)''', (sid, title, summary, skills, date_str, path, status))
            conn.commit()

    def update_activity_status(self, student_id, title, date, new_status):
        """Moves an item from 'pending' (Audit) to 'approved' (Gallery)."""
        with self._get_connection() as conn:
            conn.execute("UPDATE activities SET status=? WHERE student_id=? AND title=? AND date=?", 
                         (new_status, student_id, title, date))
            conn.commit()

    def delete_activity(self, sid, title, date):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM activities WHERE student_id=? AND title=? AND date=?", (sid, title, date))
            conn.commit()

    # --- DATA RETRIEVAL ---
    def get_student_profile(self, sid):
        with self._get_connection() as conn:
            grades = pd.read_sql("SELECT * FROM grades WHERE student_id=?", conn, params=(sid,))
            activities = pd.read_sql("SELECT * FROM activities WHERE student_id=? ORDER BY date DESC", conn, params=(sid,))
            return grades, activities

    def get_all_data_for_export(self):
        with self._get_connection() as conn:
            users = pd.read_sql("SELECT student_id, role, name FROM users", conn)
            grades = pd.read_sql("SELECT * FROM grades", conn)
            activities = pd.read_sql("SELECT * FROM activities", conn)
            return users, grades, activities

    # --- BACKUP & EXPORT ---
    def export_to_excel(self):
        """Generates an Excel file (in-memory) with all database tables."""
        users, grades, activities = self.get_all_data_for_export()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            users.to_excel(writer, sheet_name='Users', index=False)
            grades.to_excel(writer, sheet_name='Academic_Grades', index=False)
            activities.to_excel(writer, sheet_name='Portfolio_Activities', index=False)
        return output.getvalue()

    # --- GRADE MANAGEMENT ---
    def update_grade(self, sid, year, term, subject, mark):
        with self._get_connection() as conn:
            exists = conn.execute('''SELECT 1 FROM grades WHERE student_id=? AND year=? AND term=? AND subject=?''', 
                                 (sid, year, term, subject)).fetchone()
            if exists:
                conn.execute('''UPDATE grades SET mark=? WHERE student_id=? AND year=? AND term=? AND subject=?''', 
                            (mark, sid, year, term, subject))
            else:
                conn.execute('''INSERT INTO grades (student_id, year, term, subject, mark) VALUES (?,?,?,?,?)''', 
                            (sid, year, term, subject, mark))
            conn.commit()

    def delete_user(self, sid):
        """Cascading delete of a student and all related data."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM users WHERE student_id=?", (sid,))
            conn.execute("DELETE FROM grades WHERE student_id=?", (sid,))
            conn.execute("DELETE FROM activities WHERE student_id=?", (sid,))
            conn.commit()

            def get_full_portfolio_zip(self, sid):
             grades, activities = self.get_student_profile(sid)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            # 1. Prepare Excel Data
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                grades.to_excel(writer, sheet_name='Grades', index=False)
                activities.to_excel(writer, sheet_name='Portfolio', index=False)
            zip_file.writestr(f"student_{sid}_report.xlsx", excel_buffer.getvalue())
            
            # 2. Add Images
            for _, row in activities.iterrows():
                path = row.get('file_path')
                if path and os.path.exists(str(path)):
                    img_name = os.path.basename(str(path))
                    with open(str(path), 'rb') as f:
                        zip_file.writestr(f"images/{img_name}", f.read())
                        
        return zip_buffer.getvalue()