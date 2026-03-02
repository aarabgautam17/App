import sqlite3
import bcrypt

# 1. Connect (ensure this matches the filename in your app.py)
conn = sqlite3.connect("school_portal.db")
cursor = conn.cursor()

# 2. Match the exact schema from your DatabaseManager
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
    (student_id TEXT PRIMARY KEY, password BLOB, role TEXT, name TEXT)''')

# 3. Create a hashed password
# Note: bcrypt.hashpw returns a bytes object
password = "admin_password_here" 
hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# 4. Insert with Error Handling
try:
    # We use 'owner' as the ID to distinguish it from the default 'admin'
    cursor.execute("INSERT INTO users (student_id, password, role, name) VALUES (?, ?, ?, ?)", 
                   ("owner", hashed_pw, "Admin", "System Owner"))
    conn.commit()
    print(f"🚀 Success! Account 'owner' is ready.")
except sqlite3.IntegrityError:
    # If it exists, let's update the password just in case you forgot it
    cursor.execute("UPDATE users SET password = ? WHERE student_id = ?", (hashed_pw, "owner"))
    conn.commit()
    print("🔄 Admin 'owner' already existed; password has been updated!")

conn.close()