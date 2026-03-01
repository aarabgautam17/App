import sqlite3
import bcrypt

# 1. Connect to your database file
conn = sqlite3.connect("school_portal.db")
cursor = conn.cursor()

# 2. Ensure the users table exists
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
    (student_id TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)''')

# 3. Create a hashed password for 'admin123'
password = "1234567890"
hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# 4. Insert the Admin account
try:
    cursor.execute("INSERT INTO users (student_id, password, role, name) VALUES (?, ?, ?, ?)", 
                   ("owner", hashed_pw, "Admin", "Head Admin"))
    conn.commit()
    print(f"✅ Success! You can now login with ID: 'owner' and Password: '{password}'")
except sqlite3.IntegrityError:
    print("⚠️ Admin account already exists.")

conn.close()