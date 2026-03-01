import sqlite3

conn = sqlite3.connect("school_portal.db")
cursor = conn.cursor()

print("--- Current Registered Users ---")
cursor.execute("SELECT student_id, role, name FROM users")
rows = cursor.fetchall()

if not rows:
    print("No users found. The database is empty!")
else:
    for row in rows:
        print(f"ID: {row[0]} | Role: {row[1]} | Name: {row[2]}")

conn.close()